import json
from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
from src.tipboard.app.applicationconfig import getRedisPrefix
from src.tipboard.app.cache import getCache
from src.tipboard.app.properties import LOG
from src.tipboard.app.FakeData.fake_data import buildFakeDataFromTemplate
from src.tipboard.app.utils import getTimeStr
from src.tipboard.app.cache import listOfTilesFromLayout

cache = getCache()


class WSConsumer(WebsocketConsumer):
    """ Handles client connections on web sockets and listens on Redis subscriptions """

    def connect(self):
        async_to_sync(self.channel_layer.group_add)('event', self.channel_name)
        self.accept()

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)('event', self.channel_name)
        self.close()

    def receive(self, text_data, **kwargs):
        """ handle msg sended by client, by 2 way: update all tiles or update 1 specific tile """
        if 'first_connection:' in text_data:
            dashboardName = text_data.replace('first_connection:/', '')
            listOftiles = listOfTilesFromLayout(dashboardName)
            for tileId in listOftiles:
                self.update_tile_receive(tile_id=tileId, template_name=listOftiles[tileId]['tile_template'])
        else:
            for tile_id in cache.listOfTilesCached():
                self.update_tile_receive(tile_id=tile_id)

    def update_tile_receive(self, tile_id, template_name=None):
        """ Create or update the tile with value and send to the client with websocket """
        tileData = cache.get(tile_id=getRedisPrefix(tile_id))
        if tileData is None:
            if LOG:
                print(f'{getTimeStr()} (-) No data in key {tile_id} on Redis.', flush=True)
                print(f'{getTimeStr()} (-) Generating fake data for {tile_id}.', flush=True)
            data = buildFakeDataFromTemplate(tile_id, template_name, cache)
        else:
            data = json.loads(tileData)
        if isinstance(data, str):
            data = json.loads(data)
        self.send(text_data=json.dumps(data))

    def update_tile(self, data):
        """ send to client a single tile config """
        tile_id = getRedisPrefix(data['tile_id'])
        tileData = cache.get(tile_id=tile_id)
        if tileData is None:
            if LOG:
                print(f'{getTimeStr()} (-) No data in key {tile_id} on Redis.', flush=True)
            return
        data = json.loads(tileData)
        if isinstance(data, str):
            data = json.loads(data)
        self.send(text_data=json.dumps(data))
