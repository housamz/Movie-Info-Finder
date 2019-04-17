import requests  # getting links source code
import urllib  # handle url encoding
import re  # handling regular expression
import json #handling RT data as JSON

from bs4 import BeautifulSoup  # searching source code
from string import Template  # handling the html output

headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.90 Safari/537.36'}

IMDB_url = 'https://www.imdb.com/find?q=%s&s=tt&ttype=ft&ref_=fn_ftl'
MC_url	 = 'http://www.metacritic.com/search/movie/%s/results'
RT_url	 = 'https://www.rottentomatoes.com/search/?search=%s'

def find_between(s, first, last):
	try:
		start = s.index(first) + len(first)
		end = s.index(last, start)
		return s[start:end]
	except ValueError:
		return ""


def remove_u(word):
	word_with_u = (word.encode('unicode-escape')).decode("utf-8", "strict")
	if r'\u' in word_with_u: 
		return word_with_u.split('\\u')[1]
	return word


def clean_name(movie_name):
	movie_name = remove_u(movie_name.replace('-', ' '))
	movie_name = re.sub(r'([^\s\w]|_)+', '', movie_name)
	movie_name = urllib.quote(movie_name)
	return movie_name


def read_url_to_html(url):
	r = requests.get(url, headers=headers)
	s = BeautifulSoup(r.content, "lxml")
	return s


def sum_all_MC(data):
	sumall = 0
	for item in data:
		sumall += int(re.sub('[^0-9]', '', item.text))
	return sumall


def remove_non_num(text):
	return re.sub('[^0-9]', '', text)

def addData(jsonObject, jsonKey, jsonData):
	jsonObject[jsonKey] = jsonData
	if (type(jsonObject[jsonKey]) is int):
		print(jsonKey + ': ' + str(jsonObject[jsonKey]))
	else:
		print(jsonKey + ': ' + jsonObject[jsonKey])
	return jsonObject[jsonKey]


def movie_data(movie_on_IMDB):
	alldata = {}

	# Start IMDB crawling
	s = read_url_to_html(movie_on_IMDB)
	IMDB_data = s.find('div', class_='title_bar_wrapper'.split())

	addData(alldata, "name", IMDB_data.find("h1").contents[0].strip())

	year = IMDB_data.find("span", {"id": "titleYear"})

	if not year:
		return

	addData(alldata, "year", IMDB_data.find("span", {"id": "titleYear"}).text[1:-1])
	addData(alldata, "summary", s.find("div", {"class": "summary_text"}).text.strip())

	posterDiv = s.find('div', class_='poster'.split())
	if(posterDiv):
		posterImage = posterDiv.find("img")
		addData(alldata, "poster", posterImage['src'])
	else:
		addData(alldata, "poster", 'http://wpmovies.scriptburn.com/wp-content/themes/wp_movies/images/noposter.jpg')

	addData(alldata, "IMDB_link", movie_on_IMDB)

	IMDB_ratings = IMDB_data.find("span", {"itemprop": "ratingValue"})

	if IMDB_ratings:
		addData(alldata, "IMDB_rating", IMDB_data.find("span", {"itemprop": "ratingValue"}).text)
		addData(alldata, "IMDB_votes", IMDB_data.find("span", {"itemprop": "ratingCount"}).text.replace(',', ''))
	else:
		addData(alldata, "IMDB_rating", "N/A")
		addData(alldata, "IMDB_votes",  "N/A")

	name = clean_name(alldata["name"])

	# Start Meta Critic crawling
	print("starting MC")
	s = read_url_to_html(MC_url%(name))
	MC_search = s.findAll('li', class_='result'.split())
	if(MC_search):
		for result in MC_search:
			stats = result.find("div", {"class": "main_stats"})
			year = stats.find("p").text
			year = remove_non_num(year)
			if year == alldata["year"]:
				first_link = stats.find("h3", {"class": "product_title"})
				first_link = first_link.find("a")
				link = 'http://www.metacritic.com' + first_link["href"]

				print("MC link: " + link)

				s = read_url_to_html(link)
				MC_data = s.find("div", {"class": "reviews"})

				MC_users_rating = set(s.select("div.metascore_w.user.larger.movie"))
				MC_critics_rating = set(s.select("div.metascore_w.larger.movie")) - MC_users_rating

				addData(alldata, "MC_link", link)

				if(MC_critics_rating):
					addData(alldata, "MC_critics_rating", list(MC_critics_rating)[0].text)
					addData(alldata, "MC_critics_count", sum_all_MC(MC_data.select("a[href*=critic-reviews\?dist]")))
				else:
					addData(alldata, "MC_critics_rating", "N/A")
					addData(alldata, "MC_critics_count", "N/A")
				
				if (MC_users_rating):
					addData(alldata, "MC_users_rating", list(MC_users_rating)[0].text)
					addData(alldata, "MC_users_count", sum_all_MC(MC_data.select("a[href*=user-reviews\?dist]")))
				else:
					addData(alldata, "MC_users_rating", "N/A")
					addData(alldata, "MC_users_count", "N/A")
				break
			else:
				addData(alldata, "MC_link", "N/A")
				addData(alldata, "MC_users_rating", "N/A")
				addData(alldata, "MC_users_count", "N/A")
				addData(alldata, "MC_critics_rating", "N/A")
				addData(alldata, "MC_critics_count", "N/A")
	else:
		addData(alldata, "MC_link", "N/A")
		addData(alldata, "MC_users_rating", "N/A")
		addData(alldata, "MC_users_count", "N/A")
		addData(alldata, "MC_critics_rating", "N/A")
		addData(alldata, "MC_critics_count", "N/A")


	# Start Rotten Tomatoes crawling
	print("starting RT")
	s = read_url_to_html(RT_url % name)
	RT_search = s.get_text()
	
	text = find_between(RT_search, '"movies":[', ',"tvCount":')
	if(text):
		text = "[" + text
		text = json.loads(text)
		# year = find_between(text, '"year":', ',')

		for i in text:
			if i['year'] == int(alldata["year"]):
				RT_link = 'https://www.rottentomatoes.com' + i['url']
				break
			else:
				RT_link = 'N/A'

		print("RT link: " + RT_link)

		if(RT_link != 'N/A'):
			s = read_url_to_html(RT_link)
			
			addData(alldata, "RT_link", RT_link)
			RT_critics_data = s.find("span", {"class": "mop-ratings-wrap__percentage"})

			text = s.find("section", {"class": "mop-ratings-wrap__row"})

			if(text != None):
				counts = text.find_all('small')
				
				if (RT_critics_data):
					addData(alldata, "RT_critics_rating", remove_non_num(RT_critics_data.text))
					addData(alldata, "RT_critics_count", re.sub(r"\W", "", counts[0].text))
				else:
					addData(alldata, "RT_critics_rating", "N/A")
					addData(alldata, "RT_critics_count", "N/A")

				RT_users_data = s.find("span", {"class": "mop-ratings-wrap__percentage--audience"})

				if (RT_users_data):
					addData(alldata, "RT_users_rating", remove_non_num(RT_users_data.text))
					addData(alldata, "RT_users_count", re.sub(r"\W", "", counts[1].text))
				else:
					addData(alldata, "RT_users_rating", "N/A")
					addData(alldata, "RT_users_count", "N/A")
			else:
				addData(alldata, "RT_critics_rating", "N/A")
				addData(alldata, "RT_critics_count", "N/A")
				addData(alldata, "RT_users_rating", "N/A")
				addData(alldata, "RT_users_count", "N/A")
		else:
			addData(alldata, "RT_critics_rating", "N/A")
			addData(alldata, "RT_critics_count", "N/A")
			addData(alldata, "RT_users_rating", "N/A")
			addData(alldata, "RT_users_count", "N/A")
	else:
		addData(alldata, "RT_critics_rating", "N/A")
		addData(alldata, "RT_critics_count", "N/A")
		addData(alldata, "RT_users_rating", "N/A")
		addData(alldata, "RT_users_count", "N/A")

	
	print("done")

	return alldata

# print(movie_data("https://www.imdb.com/title/tt0076759"))
