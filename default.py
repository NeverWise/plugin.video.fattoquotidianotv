#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys, re, xbmcgui, httplib#, datetime
from neverwise import Util
from pyamf import remoting


class FattoQTV(object):

  _handle = int(sys.argv[1])
  _params = Util.urlParametersToDict(sys.argv[2])

  def __init__(self):

    if len(self._params) == 0: # Visualizzazione del menu.

      # Menu.
      lis = Util('http://tv.ilfattoquotidiano.it').getBSHtml(True)
      if lis != None:
        lis = lis.find('ul', id="menu-videogallery")
        lis = lis.findAll('li', id=re.compile('menu-item-[0-9]+'))
        items = []
        for li in lis:
          ul = li.find('ul')
          link = li.a['href']
          if ul == None and link.find('servizio-pubblico') == -1:
            title = Util.normalizeText(li.a.text)
            li = Util.createListItem(title, streamtype = 'video', infolabels = { 'title' : title })
            items.append([{ 'id' : 'c', 'page' : link }, li, True, True])

        # Show items.
        Util.addItems(self._handle, items)

    else:

      response = Util(self._params['page']).getHtml(True)
      if response != None:

        # Check if exist additional archive.
        archive = re.compile('<div class="go-to-archive"><h1><a href="(.+?)">').findall(response)
        if len(archive) > 0:
          response = Util(archive[0]).getHtml(True)

        if response != None:

          # Videos.
          if self._params['id'] == 'c': # Visualizzazione video di una categoria.
            videos = re.compile('<div class="video-excerpt">.+?<img.+?src="(.+?)".+?/>.+?<a.+?href="(.+?)".+?>(.+?)</a>.+?(<p>.+?</p>)?</div>').findall(response)
            items = []
            for img, link, title, descr in videos:
              title = Util.normalizeText(title)
              li = Util.createListItem(title, thumbnailImage = self._normalizeImageUrl(img), streamtype = 'video', infolabels = { 'title' : title, 'plot' : Util.normalizeText(Util.trimTags(descr)) }, isPlayable = True)
              items.append([{ 'id' : 'v', 'page' : link }, li, False, True])

            # Next page.
            nextPage = re.compile("<span class='current'>.+?</span><a.+?href='(.+?)'.+?>(.+?)</a>").findall(response)
            if len(nextPage) > 0:
              items.append([{ 'id' : 'c', 'page' : nextPage[0][0] }, Util.createItemPage(Util.normalizeText(nextPage[0][1])), True, True])

            # Show items.
            Util.addItems(self._handle, items)

          # Play video.
          elif self._params['id'] == 'v':
            title = Util.normalizeText(re.compile('<h1 class="entry-title full-title">(.+?)</h1>').findall(response)[0])
            img = self._normalizeImageUrl(re.compile('<link rel="image_src" href="(.+?)"/>').findall(response)[0])
            descr = re.compile('<span class="content"><p>(.+?)</p>').findall(response)
            if len(descr) > 0:
              descr = Util.normalizeText(Util.trimTags(descr[0]))
            else:
              descr = None

            # Video del fatto.
            videoId = re.compile('<param name="@videoPlayer" value="(.+?)"/>').findall(response)
            if len(videoId) > 0:
              playerID = 2274739660001
              publisherID = 1328010481001
              const = 'ef59d16acbb13614346264dfe58844284718fb7b'
              conn = httplib.HTTPConnection('c.brightcove.com')
              envelope = remoting.Envelope(amfVersion=3)
              envelope.bodies.append(('/1', remoting.Request(target='com.brightcove.player.runtime.PlayerMediaFacade.findMediaById', body=[const, playerID, videoId[0], publisherID], envelope=envelope)))
              conn.request('POST', '/services/messagebroker/amf?playerId={0}'.format(str(playerID)), str(remoting.encode(envelope).read()), {'content-type': 'application/x-amf'})
              response = conn.getresponse().read()
              response = remoting.decode(response).bodies[0][1].body

              if response != None:
                item = sorted(response['renditions'], key=lambda item: item['encodingRate'], reverse=True)[0]
                streamUrl = item['defaultURL']

                # Divido url da playpath.
                index = streamUrl.find('&')
                url = streamUrl[:index]
                playpath = streamUrl[index + 1:]

                # Divido url da app.
                index = url.find('/', 7)
                app = url[index + 1:]
                if app[-1:] == '/':
                  app = app[:-1]

                Util.playStream(self._handle, title, img, '{0}:1935 app={1} playpath={2}'.format(url[:index], app, playpath), 'video', { 'title' : title, 'plot' : descr })
              else:
                Util.showVideoNotAvailableDialog()
            else:

              # Video di youtube.
              videoId = re.compile('<iframe.+?src="http://www.youtube.com/embed/(.+?)\?.+?".+?></iframe>').findall(response)
              if len(videoId) > 0:
                Util.playStream(self._handle, title, img, 'plugin://plugin.video.youtube/?path=/root/video&action=play_video&videoid={0}'.format(videoId[0]), 'video', { 'title' : title, 'plot' : descr })
              else:
                # Altri video non gestiti.
                Util.showVideoNotAvailableDialog()


  def _normalizeImageUrl(self, img):
    index = img.find('?')
    if index > 0:
      img = img[:index]
    return img


# Entry point.
#startTime = datetime.datetime.now()
fc = FattoQTV()
del fc
#print '{0} azione {1}'.format(Util._addonName, str(datetime.datetime.now() - startTime))
