#!/usr/bin/env python3

# myminifactory.com newsfeed. (c) ted timmons 2018, MIT license.

import boto3
import configparser
import json
import mimetypes
import os
import requests

s3 = boto3.client('s3')

def upload(feedtxt, s3_key):
  ztxt = json.dumps(feedtxt, indent=2)
  s3.put_object(
    ACL='public-read',
    Body=ztxt,
    Bucket='dyn.tedder.me',
    Key=s3_key,
    ContentType='application/json',
    CacheControl='public, max-age=3600',
  )
  #print("published: ", s3_key)

def create_item(item):
  author = item['designer']
  retitem = {
    'id': str(item['id']),
    'url': item['url'],
    'title': item['name'],
    'content_html': item.get('description_html') or '', # .get() can return None.
    'content_text': item.get('description') or '',
    'author': {
      'name': author['username'],
      'url': author['profile_url'],
      'avatar': author['avatar_url'],
    },
    'date_published': item['published_at'],
    'tags': item['tags'],
    'attachments': [],
  }

  for i in item['images']:
    if i['is_primary']:
      #i['original']['url']
      #print(i.keys())
      retitem['image'] = i['large']['url']
      # also add to the bottom of the content; at least Newsblur doesn't use the image field.
      retitem['content_html'] = '<img src="{}"><br clear="all" />{}'.format(i['thumbnail']['url'], retitem['content_html'])
    else:
      retitem['attachments'].append({
        'mime_type': mimetypes.guess_type(i['large']['url'])[0],
        'url': i['large']['url'],
      })
  return retitem

def makefeed(params_override, page_url, s3_key, feed_title, api_key):
  params = {
    'q': '*',
    'sort': 'date',
    'featured': '0',
    'key': api_key,
  }
  params = {**params, **params_override}
  #print('params: ', params)

  searchret = requests.get('https://www.myminifactory.com/api/v2/search',
    params=params,
    headers={ 'Accept': 'application/json' }
  )

  ret = searchret.json()
  jfeed = {
    'version': 'https://jsonfeed.org/version/1',
    'title': feed_title,
    'home_page_url': page_url,
    'feed_url': 'https://dyn.tedder.me/' + s3_key,
    #'items': [create_item(i) for i in ret['items']]
    'items': []
  }
  c = 0
  for i in ret['items']:
    if any(x in i['name'].lower() for x in ['bauble', 'ornament']): continue
    jfeed['items'].append(create_item(i))
    c += 1
    if c > 40: break
  #print(json.dumps(jfeed, indent=2))
  upload(jfeed, s3_key)

# sniff our script dir, useful since we're a cron
scriptdir = os.path.dirname(os.path.realpath(__file__))
conf = configparser.ConfigParser()
conf.read(os.path.join(scriptdir, 'creds.ini'))
api_key = conf['creds']['api_key']

makefeed(
  params_override={'featured': '0'},
  page_url='https://www.myminifactory.com/search/?featured=0&sortBy=date',
  s3_key='rss/myminifactory-newest.json',
  feed_title='MyMiniFactory- Newest Items',
  api_key=api_key
)
makefeed(
  params_override={'featured': '1'},
  page_url='https://www.myminifactory.com/search/?featured=1&sortBy=date',
  s3_key='rss/myminifactory-featured.json',
  feed_title='MyMiniFactory- Featured Items',
  api_key=api_key
)



