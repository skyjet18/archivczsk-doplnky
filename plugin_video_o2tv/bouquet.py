# -*- coding: utf-8 -*-

from tools_archivczsk.generator.bouquet_xmlepg import BouquetXmlEpgGenerator, BouquetGenerator

NAME_PREFIX = "o2tv_2"

# #################################################################################################

class O2TVBouquetGenerator(BouquetGenerator):
	def __init__(self, bxeg, channel_type=None):
		BouquetGenerator.__init__(self, bxeg, channel_type)
		self.play_url_pattern = '/playlive/%s/index.mpd'


class O2TVBouquetXmlEpgGenerator(BouquetXmlEpgGenerator):
	def __init__(self, content_provider, http_endpoint, user_agent):
		self.bouquet_settings_names = ('enable_userbouquet', 'enable_adult', 'enable_xmlepg', 'enable_picons', 'player_name', 'export_md_subchannels')
		BouquetXmlEpgGenerator.__init__(self, content_provider, http_endpoint, login_settings_names=('username', 'password'), user_agent=user_agent)
		self.prefix = NAME_PREFIX # this is needed for compatiblity with old archivo2tv addon
		self.bouquet_generator = O2TVBouquetGenerator

	def logged_in(self):
		return self.cp.o2tv != None

	def get_channels_checksum(self, channel_type):
		return self.cp.checksum

	def load_channel_list(self):
		self.cp.load_channel_list()

	def get_bouquet_channels(self, channel_type=None):
		for channel in self.cp.channels:
			if channel['md_subchannel']:
				if self.cp.get_setting('export_md_subchannels') == False or not self.cp.is_supporter():
					continue

			yield {
				'name': channel['name'],
				'adult': channel['adult'],
				'picon': channel['picon'],
				'id': channel['number'] + channel['sub_number'],
				'key': str(channel['key']),
			}

	def get_xmlepg_channels(self):
		for channel in self.cp.channels:
			yield {
				'name': channel['name'],
				'id': channel['number'] + channel['sub_number'],
				'key': channel['key'],
			}

	def get_epg(self, channel, fromts, tots):
		export_md_subchannels = self.cp.get_setting('export_md_subchannels') and self.cp.is_supporter()

		for event in self.cp.o2tv.get_channel_epg(channel['key'], fromts, tots):
			if export_md_subchannels == False and event.get('mosaic_id'):
				event2 = self.cp.o2tv.get_mosaic_info(event['mosaic_id'])
				if event2:
					event = event2
			yield event

# #################################################################################################
