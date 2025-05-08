# -*- coding: utf-8 -*-
import os
import subprocess
from Plugins.Extensions.archivCZSK.engine.tools.stbinfo import stbinfo

tmp_file_id = 1
DECRYPT_CMD = os.path.join(os.path.dirname(__file__), 'bin', 'mp4edit_%s' % stbinfo.hw_arch)

def mp4remove_cenc(data):
	# this is very simple and unefective implementation that blocks reactor and that is definitely not what we want ...
	# needs complete rewrite to async ...
	global tmp_file_id

	# create temp file with segment data
	tmp_file_name_in = os.path.join( '/tmp', '._xin_%d.m4s' % tmp_file_id)
	tmp_file_name_out = os.path.join( '/tmp', '._xout_%d.m4s' % tmp_file_id)
	tmp_file_id += 1
	if tmp_file_id >= 1000:
		tmp_file_id = 1

	with open(tmp_file_name_in, 'wb') as f:
		f.write(data)

	cmd = [DECRYPT_CMD]

	cmd.append('--remove')
	cmd.append('moov/trak/mdia/minf/stbl/stsd/encv/sinf')
	cmd.append(tmp_file_name_in)
	cmd.append(tmp_file_name_out)

	try:
		subprocess.check_call( cmd )
	except:
		data_out = None
	else:
		with open(tmp_file_name_out, 'rb') as f:
			data_out = f.read()
	finally:
		os.remove(tmp_file_name_in)
		try:
			os.remove(tmp_file_name_out)
		except:
			pass

	# this needs to be properly fixed
	return data_out.replace(b'encv', b'avc1')
