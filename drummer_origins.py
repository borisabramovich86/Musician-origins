
import requests
import re
import os
from lxml import html
from lxml.etree import tostring
from flask import Flask, escape, request
from flask_cors import CORS
from flask.json import jsonify


GOOGLE_MAPS_API_KEY = os.environ['GOOGLE_MAPS_API_KEY']
drummer_markers = []
guitarists_markers = []
bassists_markers = []

app = Flask(__name__)
CORS(app)

def write_to_file_found(file_ref, drummer_name, lat, lng):
	file_ref.write("{},{},{}".format(drummer_name, lat, lng))
	file_ref.write('\n')

def write_to_file_not_found(file_ref, drummer_name):
	file_ref.write(drummer_name)
	file_ref.write('\n')

def create_map_marker(markers, drummer_name, drummer_city, found_file_ref, missing_file_ref):
	url = 'https://maps.googleapis.com/maps/api/place/findplacefromtext/json'
	response = requests.get(url = url, params={'input': drummer_city, 
												'inputtype': 'textquery',
												'fields': 'geometry',
												'key': GOOGLE_MAPS_API_KEY})
	parsed_json = response.json()
	candidates = parsed_json['candidates']
	if len(candidates) > 0:
		location = candidates[0]['geometry']['location']
		lat = location['lat']
		lng = location['lng']
		marker_string = {"lat": lat, "lng": lng, "name": drummer_name}
		markers.append(marker_string)
		write_to_file_found(found_file_ref, drummer_name, lat, lng)
	else:
		MissingDrummers=open('drummers_missing','a')
		write_to_file_not_found(missing_file_ref, drummer_name)

def get_html_tree_from_url(url):
	page = requests.get(url)
	return html.fromstring(page.content)

def get_city_from_infobox(tree, subject_text):
	born_in_list = tree.xpath('//*[contains(@class, \'infobox\')]//th[contains(text(),\'{}\')]/parent::tr/td/a'.format(subject_text))
	if len(born_in_list) > 0:
		born_in = born_in_list[0]
		born_in_place = born_in.get('title')
		born_in_link = born_in.get('href')
		print(born_in_place)
		print()
		return born_in_place
			
def get_city_from_wiki(drummer_wiki_link):
	url = 'https://en.wikipedia.org/{}'.format(drummer_wiki_link)
	tree = get_html_tree_from_url(url)
	drummer_city = get_city_from_infobox(tree, 'Born')

	if (not drummer_city):
		drummer_city = get_city_from_infobox(tree, 'Origin')

	return drummer_city

def get_markers(wiki_name, markers, found_file_ref, missing_file_ref):
	tree = get_html_tree_from_url('https://en.wikipedia.org/wiki/{}'.format(wiki_name))
	drummers = tree.xpath('//*[contains(@class, \'mw-parser-output\')]/ul/li/a[1]')

	for drummer in drummers:
		drummer_name = drummer.get("title")
		print(drummer_name)
		drummer_city = get_city_from_wiki(drummer.get("href"))
		create_map_marker(markers, drummer_name, drummer_city, found_file_ref, missing_file_ref)

	return markers

def load_markers_from_file(file_name, markers):
	file1=open(file_name, "r")
	Lines = file1.readlines()

	for line in Lines: 
		line_split = line.split(",")
		lat = float(line_split[1].replace("\n", ""))
		lng = float(line_split[2])
		name = line_split[0]
		marker_string = {"lat": lat, "lng": lng, "name": name}
		markers.append(marker_string)

def get_musician_data(wiki_name, found_file, missing_file, markers):
	FoundFile=open(found_file,'a')
	MissingFile=open(missing_file,'a')

	load_markers_from_file(found_file, markers)

	if len(markers) > 0:
		return jsonify({'markers':markers})

	return jsonify({'markers': get_markers(wiki_name, markers, FoundFile, MissingFile)})

	FoundFile.close()
	MissingFile.close()

@app.route('/drummers')
def drummers():
	print("getting drummers")
	return get_musician_data("List_of_drummers", 'drummers_found', 'drummers_missing', drummer_markers)

@app.route('/guitarists')
def guitarists():
	print("getting guitarists")
	return get_musician_data("List_of_guitarists", 'guitarists_found', 'guitarists_missing', guitarists_markers)

@app.route('/bassists')
def bassists():
	print("getting bassists")
	return get_musician_data("List_of_bass_guitarists", 'bassists_found', 'bassists_missing', bassists_markers)
#env FLASK_APP=drummer_origins.py flask run