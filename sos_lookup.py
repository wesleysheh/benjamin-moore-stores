#!/usr/bin/env python3
"""SOS lookup script - searches each state's Secretary of State for business owners."""
import json, time, sys, urllib.parse, re
import requests
from urllib.parse import quote

HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}

def search_nv_sos(name):
    """Nevada SOS - uses their AJAX endpoint"""
    session = requests.Session()
    session.headers.update(HEADERS)
    # Get the search page first for cookies
    session.get('https://esos.nv.gov/EntitySearch/OnlineEntitySearch', timeout=15)
    # Search
    r = session.post('https://esos.nv.gov/EntitySearch/BusinessSearchResult', 
                     data={'SearchType':'Contains','EntityName':name,'SearchbyOfficerRA':'false'},
                     timeout=15)
    return r.text

def search_co_sos(name):
    """Colorado SOS - has an API"""
    r = requests.get(f'https://www.sos.state.co.us/biz/BusinessEntityCriteriaExt.do?nameTyp=ENTITY&entityName={quote(name)}&srchTyp=ENTITY', 
                     headers=HEADERS, timeout=15)
    return r.text

def search_nm_sos(name):
    """New Mexico SOS"""
    r = requests.get(f'https://portal.sos.state.nm.us/BFS/online/CorporationBusinessSearch/CorporationBusinessSearchSummary?q={quote(name)}',
                     headers=HEADERS, timeout=15)
    return r.text

def search_az_sos(name):
    """Arizona Corporation Commission"""
    r = requests.get(f'https://ecorp.azcc.gov/EntitySearch/Index', headers=HEADERS, timeout=15)
    return r.text

def search_wy_sos(name):
    """Wyoming SOS"""
    r = requests.get(f'https://wyobiz.wyo.gov/Business/FilingSearch.aspx', headers=HEADERS, timeout=15)
    return r.text

def search_mt_sos(name):
    """Montana SOS"""
    r = requests.get(f'https://biz.sosmt.gov/search', headers=HEADERS, timeout=15)
    return r.text

def search_ut_sos(name):
    """Utah Division of Corporations"""
    r = requests.get(f'https://secure.utah.gov/bes/index.html', headers=HEADERS, timeout=15)
    return r.text

def search_id_sos(name):
    """Idaho SOS - has an API"""
    r = requests.get(f'https://sosbiz.idaho.gov/api/Records/businesssearch?SearchType=Contains&SearchValue={quote(name)}&SearchCategory=BusinessName',
                     headers=HEADERS, timeout=15)
    return r.text

if __name__ == '__main__':
    # Test NV
    result = search_nv_sos('MESQUITE LUMBER')
    print(result[:1000])
