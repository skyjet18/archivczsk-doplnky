# -*- coding: utf-8 -*-

import re
from collections import OrderedDict
import requests

from ..compat import urljoin

# ##################################################################################################################

class AttrValue(object):
	def __init__(self, value):
		if value.startswith('"'):
			self.value = value[1:-1]
			self.use_qm = True
		else:
			self.value = value
			self.use_qm = False

	def __str__(self):
		return self.value

	def __eq__(self, value):
		return self.value == value

	def export(self):
		if self.use_qm:
			return '"%s"' % self.value
		else:
			return self.value

# ##################################################################################################################

class PlaylistHeader(object):
	def __init__(self, playlist_url, attrs={}):
		self.playlist_url = playlist_url
		self.attrs = attrs
		if 'URI' in self.attrs:
			del self.attrs['URI']

	def __getitem__(self, key):
		return str(self.attrs[key])

	def __setitem__(self, key, value):
		self.attrs[key] = value

	def get(self, name, default=None):
		try:
			return self[name]
		except:
			return default

	def group(self):
		return self.get("GROUP-ID")

	def __str__(self):
		if self.get('TYPE') in ('AUDIO', 'SUBTITLES'):
			if self.playlist_url:
				return '#EXT-X-MEDIA:' + ','.join('%s=%s' % (k, v.export()) for k, v in self.attrs.items()) + ',URI="%s"' % self.playlist_url
			else:
				# audio variant can be without url - audio is embedded to video track (mostly TS container)
				return '#EXT-X-MEDIA:' + ','.join('%s=%s' % (k, v.export()) for k, v in self.attrs.items())
		else:
			return '#EXT-X-STREAM-INF:' + ','.join('%s=%s' % (k, v.export()) for k, v in self.attrs.items()) + '\n' + self.playlist_url

# ##################################################################################################################

class SegmentHeader(object):
	def __init__(self, segment_url, attrs='', key={}):
		self.segment_url = segment_url
		self.duration = attrs.split(',', 1)[0]
		self.key = key

	def __str__(self):
		if self.key:
			key='#EXT-X-KEY:{}\n'.format(','.join('%s=%s' % (k, v.export()) for k, v in self.key.items()))
		else:
			key = ''

		return '{}#EXTINF:{},\n{}'.format(key, self.duration, self.segment_url)

# ##################################################################################################################

class HlsPlaylist(object):
	def __init__(self, url):
		self.mp_url = url
		self.header = []
		self.video_playlists = []
		self.audio_playlists = []
		self.subtitles_playlists = []
		self.segments = []
		self.finished = False

	# ##################################################################################################################

	def load_http_data(self):
		resp = requests.get(self.mp_url)
		resp.raise_for_status()

		# update playlist url after redirect
		self.mp_url = resp.url
		return resp.text

	# ##################################################################################################################
	@staticmethod
	def parse_attributes(line):
		attr = OrderedDict()
		for a in re.findall(r'(?:[^\s,"]|"(?:\\.|[^"])*")+', line):
			s = a.split('=')
			value = '='.join(s[1:])
			attr[s[0]] = AttrValue(value)

		return attr

	# ##################################################################################################################

	def add_video_playlist(self, attrs, playlist_url):
		p = PlaylistHeader(playlist_url, attrs)
		self.video_playlists.append(p)

	# ##################################################################################################################

	def add_media_playlist(self, attrs, key={}):
		playlist_type = attrs.get('TYPE')

		if playlist_type == 'AUDIO':
			p = PlaylistHeader(str(attrs['URI']) if 'URI' in attrs else None, attrs)
			self.audio_playlists.append(p)
		elif playlist_type == 'SUBTITLES':
			p = PlaylistHeader(str(attrs['URI']), attrs)
			self.subtitles_playlists.append(p)

	# ##################################################################################################################

	def add_segment(self, attrs, segment_url, key={}):
		s = SegmentHeader(segment_url, attrs, key)
		self.segments.append(s)

	# ##################################################################################################################

	def parse(self, playlist_data):
		attrs = {}
		key = {}
		in_header = True
		video_playlist = False

		for line in iter(playlist_data.splitlines()):
			line = line.strip()
			if not line:
				continue

			if not line.startswith('#'):
				if video_playlist:
					self.add_video_playlist(attrs, line)
				else:
					self.add_segment(attrs, line, key)
					key = {}
				attrs = {}

			elif line.startswith('#EXT-X-STREAM-INF:'):
				in_header = False
				video_playlist = True
				attrs = self.parse_attributes(line[18:])
			elif line.startswith('#EXTINF:'):
				in_header = False
				video_playlist = False
				attrs = line[8:]
			elif line.startswith('#EXT-X-MEDIA:'):
				in_header = False
				self.add_media_playlist(self.parse_attributes(line[13:]))
			elif line.startswith('#EXT-X-KEY:'):
				key = self.parse_attributes(line[11:])
			elif line == '#EXT-X-ENDLIST':
				self.finished = True
			elif in_header:
				self.header.append(line)

	# ##################################################################################################################

	def process(self, mp_data=None):
		if not mp_data:
			mp_data = self.load_http_data(self.mp_url)
		self.parse(mp_data)

		# filter out not needed data from master playlist in order to speed up all another operations
		self.filter_master_playlist()
		self.cleanup_master_playlist()
		self.process_playlist_urls()

		return self.to_string()

	# ##################################################################################################################

	def filter_master_playlist(self, video_variants=False, max_bandwidth=None):
		# remove audio with scene description
		self.audio_playlists = list(filter(lambda p: "public.accessibility.describes-video" not in p.get('CHARACTERISTICS','').split(','), self.audio_playlists))

		# remove forced languages for non CS, SK language
		self.subtitles_playlists = list(filter(lambda p: p.get('LANGUAGE','').split('-')[0] in ('cs', 'sk') or p.get('FORCED') == 'NO', self.subtitles_playlists))

		# just simple default filter that gets the best stream by bandwidth
		playlists = self.video_playlists
		playlists = sorted(playlists, key=lambda p: int(str(p.get('BANDWIDTH',0))), reverse=True)

		if max_bandwidth:
			max_bandwidth = int(max_bandwidth)
			playlists2 = playlists
			playlists = list(filter(lambda p: int(str(p.get('BANDWIDTH',0))) <= max_bandwidth, playlists))

			if not playlists:
				# no stream passed max bandwith filtering, so choose only the worst one
				playlists = [playlists2[-1]]

		if video_variants == False:
			# if no video variants are enabled, then use only one video stream
			self.video_playlists = [playlists[0]]

	# ##################################################################################################################

	def cleanup_master_playlist(self):
		# cleans unused audio and subtitles playlists out of master playlist - should be called after calling filter_master_playlist()
		sub_to_keep = {}
		audio_to_keep = {}
		for p in self.video_playlists:
			audio_group = p.get('AUDIO')
			if audio_group:
				audio_to_keep[str(audio_group)] = True

			subtitle_group = p.get('SUBTITLES')
			if subtitle_group:
				sub_to_keep[str(subtitle_group)] = True

		self.audio_playlists = list(filter(lambda p: p.group() in audio_to_keep, self.audio_playlists))
		self.subtitles_playlists = list(filter(lambda p: p.group() in sub_to_keep, self.subtitles_playlists))

	# ##################################################################################################################

	def process_playlist_urls(self):
		for p in self.audio_playlists:
			if p.playlist_url:
				p.playlist_url = urljoin(self.mp_url, p.playlist_url)

		for p in self.subtitles_playlists:
			p.playlist_url = urljoin(self.mp_url, p.playlist_url)

		for p in self.video_playlists:
			p.playlist_url = urljoin(self.mp_url, p.playlist_url)

		for s in self.segments:
			s.segment_url = urljoin(self.mp_url, p.segment_url)

	# ##################################################################################################################

	def to_string(self, video_idx=None, audio_idx=None, subtitle_idx=None):
		if video_idx is not None and isinstance(video_idx, int):
			video_idx = [video_idx]

		if audio_idx is not None and isinstance(audio_idx, int):
			audio_idx = [audio_idx]

		if subtitle_idx is not None and isinstance(subtitle_idx, int):
			subtitle_idx = [subtitle_idx]

		data = []
		data.extend(self.header)

		if self.segments:
			for s in self.segments:
				data.append(str(s))

			if self.finished:
				data.append('#EXT-X-ENDLIST')
		else:
			for i, p in enumerate(self.audio_playlists):
				if audio_idx is None or i in audio_idx:
					data.append(str(p))

			for i, p in enumerate(self.subtitles_playlists):
				if subtitle_idx is None or i in subtitle_idx:
					data.append(str(p))

			for i, p in enumerate(self.video_playlists):
				if video_idx is None or i in video_idx:
					data.append(str(p))

		return '\n'.join(data) + '\n'

	# ##################################################################################################################
