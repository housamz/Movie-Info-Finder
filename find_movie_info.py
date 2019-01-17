import requests  # getting links source code
import urllib  # handle url encoding
import re  # handling regular expression

from bs4 import BeautifulSoup  # searching source code
from string import Template # handling the html output

headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.90 Safari/537.36'}

IMDB_url = 'https://www.imdb.com/find?q=%s&s=tt&ttype=ft&ref_=fn_ftl'
MC_url	 = 'http://www.metacritic.com/search/movie/%s/results'
RT_url	 = 'https://www.rottentomatoes.com/search/?search=%s'

htmltemplate = Template('<img class="pull-left" style="margin:0 10px" src="$poster"><h5 class="card-title">$name <small>($year)</small></h5><p>$summary</p><table class="table table-striped"><thead><tr><th colspan="2">&nbsp;</th><th><a href="$IMDB_link" target="_blank">IMDB</a></th><th><a href="$MC_link" target="_blank">MC</a></th><th><a href="$RT_link" target="_blank">RT</a></th></tr></thead><tbody><tr><td rowspan="2">Critics</td><td>Rating</td><td>N/A</td><td>$MC_critics_rating</td><td>$RT_critics_rating</td></tr><tr><td>Votes</td><td>N/A</td><td>$MC_critics_count</td><td>$RT_critics_count</td></tr><tr><td rowspan="2">Users</td><td>Rating</td><td>$IMDB_rating</td><td>$MC_users_rating</td><td>$RT_users_rating</td></tr><tr><td>Votes</td><td>$IMDB_votes</td><td>$MC_users_count</td><td>$RT_users_count</td></tr></tbody></table>')

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


def movie_data(movie_on_IMDB):
	alldata = {}

	# Start IMDB crawling
	s = read_url_to_html(movie_on_IMDB)
	IMDB_data = s.find('div', class_='title_bar_wrapper'.split())

	alldata["name"] = IMDB_data.find("h1").contents[0].strip()

	year = IMDB_data.find("span", {"id": "titleYear"})

	if not year:
		return

	alldata["year"] = IMDB_data.find("span", {"id": "titleYear"}).text[1:-1]
	alldata["summary"] = s.find("div", {"class": "summary_text"}).text.strip()

	posterDiv = s.find('div', class_='poster'.split())
	if(posterDiv):
		posterImage = posterDiv.find("img")
		alldata["poster"] = posterImage['src']
	else:
		alldata["poster"] = 'http://wpmovies.scriptburn.com/wp-content/themes/wp_movies/images/noposter.jpg'

	print alldata["poster"]

	alldata["IMDB_link"] = movie_on_IMDB

	IMDB_ratings = IMDB_data.find("span", {"itemprop": "ratingValue"})

	if IMDB_ratings:
		alldata["IMDB_rating"] = IMDB_data.find("span", {"itemprop": "ratingValue"}).text
		alldata["IMDB_votes"] = IMDB_data.find("span", {"itemprop": "ratingCount"}).text.replace(',', '')
	else:
		alldata["IMDB_rating"] = "none"
		alldata["IMDB_votes"] = "none"

	name = clean_name(alldata["name"])

	# Start Meta Critic crawling
	print "starting MC"
	s = read_url_to_html(MC_url%(name))
	MC_search = s.findAll('li', class_='result'.split())
	for result in MC_search:
		stats = result.find("div", {"class": "main_stats"})
		year = stats.find("p").text
		year = remove_non_num(year)
		if year == alldata["year"]:
			first_link = stats.find("h3", {"class": "product_title"})
			first_link = first_link.find("a")
			link = 'http://www.metacritic.com' + first_link["href"]

			print "found MC link: " + link

			s = read_url_to_html(link)
			MC_data = s.find("div", {"class": "reviews"})

			MC_users_rating = set(s.select("div.metascore_w.user.larger.movie"))
			MC_critics_rating = set(s.select("div.metascore_w.larger.movie")) - MC_users_rating

			alldata["MC_link"] = link

			if(MC_critics_rating):
				alldata["MC_critics_rating"] = list(MC_critics_rating)[0].text
				alldata["MC_critics_count"] = sum_all_MC(MC_data.select("a[href*=critic-reviews\?dist]"))
			else:
				alldata["MC_critics_rating"] = "none"
				alldata["MC_critics_count"] = "none"
			
			if (MC_users_rating):
				alldata["MC_users_rating"] = list(MC_users_rating)[0].text
				alldata["MC_users_count"] = sum_all_MC(MC_data.select("a[href*=user-reviews\?dist]"))
			else:
				alldata["MC_users_rating"] = "none"
				alldata["MC_users_count"] = "none"

	# Start Rotten Tomatoes crawling
	print "starting RT"
	s = read_url_to_html(RT_url % name)
	RT_search = s.get_text()
	
	text = find_between(RT_search, '"movies":[', ',"tvCount":')
	year = find_between(text, '"year":', ',')
	if year == alldata["year"]:
		link = 'https://www.rottentomatoes.com' + find_between(text, ',"url":"', '"')

		print "found RT link: " + link

		s = read_url_to_html(link)
		
		alldata["RT_link"] = link
		RT_critics_data = s.find("div", {"class": "critic-score"})
		
		if (RT_critics_data):
			alldata["RT_critics_rating"] = remove_non_num(RT_critics_data.text)
			alldata["RT_critics_count"] = find_between(s.find("div", {"id": "scoreStats"}).text, "Reviews Counted: ", "\n")
		else:
			alldata["RT_critics_rating"] = "none"
			alldata["RT_critics_count"] = "none"

		alldata["RT_users_rating"] = remove_non_num(s.find("div", {"class": "audience-score"}).text)
		alldata["RT_users_count"] = find_between(s.find("div", {"class": "audience-info"}).text, "User Ratings:\n", "\n").strip().replace(',', '')
		print "done"

		alldata["html"] = htmltemplate.substitute(poster = alldata["poster"], name = alldata["name"], year = alldata["year"], summary = alldata["summary"], IMDB_link = alldata["IMDB_link"], MC_link = alldata["MC_link"], RT_link = alldata["RT_link"], MC_critics_rating = alldata["MC_critics_rating"], RT_critics_rating = alldata["RT_critics_rating"], MC_critics_count = alldata["MC_critics_count"], RT_critics_count = alldata["RT_critics_count"], IMDB_rating = alldata["IMDB_rating"], MC_users_rating = alldata["MC_users_rating"], RT_users_rating = alldata["RT_users_rating"], IMDB_votes = alldata["IMDB_votes"], MC_users_count = alldata["MC_users_count"], RT_users_count = alldata["RT_users_count"])

	return alldata

# print movie_data("https://www.imdb.com/title/tt0076759")
