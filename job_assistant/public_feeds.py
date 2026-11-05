"""Bounded public feeds with local refresh limits; never logs in or submits applications."""
import json
import math
import os
from pathlib import Path
import time
from urllib.request import Request,urlopen
from .models import contains,clean
from .sources import plain_text,validate_rows

FEEDS={
 'remotive':{'url':'https://remotive.com/api/remote-jobs?limit=100','refresh_seconds':21600},
 'arbeitnow':{'url':'https://www.arbeitnow.com/api/job-board-api?page=1','refresh_seconds':3600},
}


def parse_remotive(payload):
    if not isinstance(payload,dict) or not isinstance(payload.get('jobs'),list):
        raise ValueError('Remotive schema changed: expected jobs list')
    rows=[]
    for item in payload['jobs']:
        if not isinstance(item,dict):raise ValueError('Invalid Remotive record')
        location=clean(item.get('candidate_required_location'))
        rows.append({'title':item.get('title'),'company':item.get('company_name'),'url':item.get('url'),
            'source_url':item.get('url'),'description':plain_text(item.get('description')),'location':location,
            'workplace':'remote','eligible_countries':['WORLDWIDE'] if location.casefold() in {'worldwide','anywhere in the world'} else [],
            'salary':item.get('salary',''),'source':'Remotive'})
    return rows


def parse_arbeitnow(payload):
    if not isinstance(payload,dict) or not isinstance(payload.get('data'),list):
        raise ValueError('Arbeitnow schema changed: expected data list')
    rows=[]
    for item in payload['data']:
        if not isinstance(item,dict):raise ValueError('Invalid Arbeitnow record')
        rows.append({'title':item.get('title'),'company':item.get('company_name'),'url':item.get('url'),
            'source_url':item.get('url'),'description':plain_text(item.get('description')),
            'location':item.get('location',''),'workplace':'remote' if item.get('remote') is True else 'unknown',
            'eligible_countries':[],'source':'Arbeitnow'})
    return rows

PARSERS={'remotive':parse_remotive,'arbeitnow':parse_arbeitnow}


def fetch_public_feed(provider,queries,limit,cache_dir,opener=urlopen,clock=time.time):
    if provider not in FEEDS:raise ValueError('Unknown public feed')
    if not 1<=limit<=1000:raise ValueError('Feed limit must be between 1 and 1000')
    if not cache_dir:raise ValueError('Public feeds require a persistent cache directory')
    config=FEEDS[provider];directory=Path(cache_dir);directory.mkdir(parents=True,exist_ok=True)
    cache=directory/(provider+'.json');lock=directory/(provider+'.lock');attempt=directory/(provider+'.attempt.json')
    notes=[f'{provider}: bounded feed snapshot; not exhaustive coverage or verified applicant eligibility']
    if provider=='remotive':notes.append('Remotive source links retained; public data may be delayed by 24 hours; not for onward syndication')
    def fresh():
        if not cache.is_file():return None
        if cache.stat().st_size>8_100_000:raise ValueError('Cache exceeds size cap')
        value=json.loads(cache.read_text(encoding='utf-8'))
        if value.get('provider')!=provider or value.get('url')!=config['url']:raise ValueError('Cache origin mismatch')
        fetched=value.get('fetched_at')
        if type(fetched) not in (int,float) or not math.isfinite(fetched):raise ValueError('Invalid cache timestamp')
        age=clock()-fetched
        if age<0:raise ValueError('Clock moved backwards; refusing early refresh')
        if 0<=age<config['refresh_seconds']:return value['payload']
        return None
    acquired=False
    try:
        payload=fresh()
        if payload is None:
            try:
                fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
                os.close(fd);acquired=True
            except FileExistsError:
                return [],notes+[f'{provider}: refresh lock active; no concurrent network request made']
            payload=fresh()
            if payload is None:
                if attempt.exists():
                    if attempt.stat().st_size>1024:raise ValueError('Invalid attempt record size')
                    attempted=json.loads(attempt.read_text(encoding='utf-8')).get('attempted_at')
                    if type(attempted) not in (int,float) or not math.isfinite(attempted):raise ValueError('Invalid attempt timestamp')
                    if clock()-attempted<config['refresh_seconds']:
                        return [],notes+[f'{provider}: refresh cooldown active after prior attempt; no network request made']
                attempt.write_text(json.dumps({'attempted_at':clock()}),encoding='utf-8')
                request=Request(config['url'],headers={'Accept':'application/json','User-Agent':'JobsApplier/2.0 (personal research) '})
                with opener(request,timeout=15) as response:raw=response.read(8_000_001)
                if len(raw)>8_000_000:raise ValueError('Feed exceeds 8 MB')
                payload=json.loads(raw)
                # Validate structure before preserving a reusable response.
                PARSERS[provider](payload)
                temporary=cache.with_suffix('.tmp')
                temporary.write_text(json.dumps({'provider':provider,'url':config['url'],'fetched_at':clock(),'payload':payload}),encoding='utf-8')
                os.replace(temporary,cache)
        rows=PARSERS[provider](payload)
        if len(rows)>10000:raise ValueError('Feed contains too many rows')
        selected=[r for r in rows if not queries or any(contains(clean(r.get('title')),q) for q in queries)]
        jobs,invalid=validate_rows(selected,provider)
        return jobs[:limit],notes+invalid
    except Exception as exc:
        return [],notes+[f'{provider}: unavailable ({type(exc).__name__}); no successful empty-search claim']
    finally:
        if acquired:
            try:lock.unlink()
            except FileNotFoundError:pass
