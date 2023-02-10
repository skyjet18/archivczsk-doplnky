# -*- coding: utf-8 -*-

from tools_archivczsk.contentprovider.archivczsk_provider import ArchivCZSKContentProvider
from tools_archivczsk.http_handler.playlive import PlayliveTVHTTPRequestHandler
from Plugins.Extensions.archivCZSK.engine.httpserver import archivCZSKHttpServer
from .provider import SledovaniTVContentProvider

# #################################################################################################

def main(addon):
	cp = SledovaniTVContentProvider(addon.settings, data_dir=addon.get_info('profile'), http_endpoint=archivCZSKHttpServer.getAddonEndpoint(addon.id), bgservice=addon.bgservice)
	archivCZSKHttpServer.registerRequestHandler(PlayliveTVHTTPRequestHandler(cp, addon))
	return ArchivCZSKContentProvider(cp, addon)

