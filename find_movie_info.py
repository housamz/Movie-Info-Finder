# getting links source code
import requests

# handle url encoding
try:
    from urllib import quote  # Python 2.X
except ImportError:
    from urllib.parse import quote  # Python 3+

# handling regular expression
import re

# searching source code
from bs4 import BeautifulSoup

headers = {'User-Agent':
           'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.90 Safari/537.36'}

imdb_url = 'https://www.imdb.com/find?q=%s&s=tt&ttype=ft&ref_=fn_ftl'
mc_url = 'http://www.metacritic.com/search/movie/%s/results'
rt_url = 'https://www.rottentomatoes.com/napi/search/?query=%s'


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
    movie_name = quote(movie_name)
    return movie_name


def read_url_to_html(url):
    r = requests.get(url, headers=headers)
    s = BeautifulSoup(r.content, "lxml")
    return s


def read_url_to_json(url):
    r = requests.get(url)
    return r.json()


def sum_all_mc(data):
    sum_all = 0
    for item in data:
        sum_all += int(re.sub('[^0-9]', '', item.text))
    return sum_all


def remove_non_num(text):
    return re.sub('[^0-9]', '', text)


def add_data(json_object, json_key, json_data):
    if type(json_data) is int:
        json_object[json_key] = str('{:,}'.format(json_data))
    else:
        json_object[json_key] = json_data
    print(json_key + ': ' + json_object[json_key])
    return json_object[json_key]


def make_int(entry):
    if entry != "NA" \
            and entry != "tbd"\
            and entry != '':
        return int(entry)
    else:
        return entry


def find_sum(*x):
    c = 0
    total = 0
    for item in x:
        if item != "N/A" and item != "tbd":
            c += 1
            item = item.replace('.', '')
            total += int(item)
    if c == 0:
        return "N/A"
    return int(total / c)


def movie_data(movie_on_imdb):
    all_data = {}

    # Start IMDB crawling
    s = read_url_to_html(movie_on_imdb)
    imdb_data = s.find('div', class_='title_bar_wrapper'.split())
    add_data(all_data, "name", imdb_data.find("h1").contents[0].strip())

    year = imdb_data.find("span", {"id": "titleYear"})

    if not year:
        return

    add_data(all_data, "year", imdb_data.find("span", {"id": "titleYear"}).text[1:-1])
    add_data(all_data, "summary", s.find("div", {"class": "summary_text"}).text.strip())

    poster_div = s.find('div', class_='poster'.split())
    if poster_div:
        poster_image = poster_div.find("img")
        add_data(all_data, "poster", poster_image['src'])
    else:
        add_data(all_data, "poster", 'http://wpmovies.scriptburn.com/wp-content/themes/wp_movies/images/noposter.jpg')

    add_data(all_data, "IMDB_link", movie_on_imdb)

    imdb_ratings = imdb_data.find("span", {"itemprop": "ratingValue"})

    if imdb_ratings:
        add_data(all_data, "IMDB_rating", imdb_data.find("span", {"itemprop": "ratingValue"}).text)
        add_data(all_data, "IMDB_votes", int(imdb_data.find("span", {"itemprop": "ratingCount"}).text.replace(',', '')))
    else:
        add_data(all_data, "IMDB_rating", "N/A")
        add_data(all_data, "IMDB_votes", "N/A")

    name = clean_name(all_data["name"])

    # Start Meta Critic crawling
    print("starting MC")
    s = read_url_to_html(mc_url % name)
    mc_search = s.findAll('li', class_='result'.split())
    if mc_search:
        for result in mc_search:
            stats = result.find("div", {"class": "main_stats"})
            year = stats.find("p").text
            year = remove_non_num(year)
            if year == all_data["year"]:
                first_link = stats.find("h3", {"class": "product_title"})
                first_link = first_link.find("a")
                link = 'http://www.metacritic.com' + first_link["href"]

                s = read_url_to_html(link)
                mc_data = s.find("div", {"class": "reviews"})

                mc_users_rating = set(s.select("div.metascore_w.user.larger.movie"))
                mc_critics_rating = set(s.select("div.metascore_w.larger.movie")) - mc_users_rating

                add_data(all_data, "MC_link", link)

                if mc_critics_rating:
                    add_data(all_data, "MC_critics_rating", list(mc_critics_rating)[0].text)
                    add_data(all_data, "MC_critics_count", sum_all_mc(mc_data.select(r"a[href*=critic-reviews\?dist]")))
                else:
                    add_data(all_data, "MC_critics_rating", "N/A")
                    add_data(all_data, "MC_critics_count", "N/A")

                if mc_users_rating:
                    add_data(all_data, "MC_users_rating", list(mc_users_rating)[0].text)
                    add_data(all_data, "MC_users_count", sum_all_mc(mc_data.select(r"a[href*=user-reviews\?dist]")))
                else:
                    add_data(all_data, "MC_users_rating", "N/A")
                    add_data(all_data, "MC_users_count", "N/A")
                break
            else:
                add_data(all_data, "MC_link", "N/A")
                add_data(all_data, "MC_users_rating", "N/A")
                add_data(all_data, "MC_users_count", "N/A")
                add_data(all_data, "MC_critics_rating", "N/A")
                add_data(all_data, "MC_critics_count", "N/A")
    else:
        add_data(all_data, "MC_link", "N/A")
        add_data(all_data, "MC_users_rating", "N/A")
        add_data(all_data, "MC_users_count", "N/A")
        add_data(all_data, "MC_critics_rating", "N/A")
        add_data(all_data, "MC_critics_count", "N/A")

    # Start Rotten Tomatoes crawling
    print("starting RT")
    s = read_url_to_json(rt_url % name)

    rt_link = 'N/A'

    print(s)

    for i in s["movies"]:
        if i['year'] == int(all_data["year"]):
            rt_link = 'https://www.rottentomatoes.com' + i['url']
            break

    if rt_link != 'N/A':
        s = read_url_to_html(rt_link)

        add_data(all_data, "RT_link", rt_link)
        rt_critics_data = s.find("span", {"class": "mop-ratings-wrap__percentage"})

        text = s.find("section", {"class": "mop-ratings-wrap__row"})

        if text is not None:
            counts = text.find_all('small')

            if rt_critics_data:
                add_data(all_data, "RT_critics_rating", remove_non_num(rt_critics_data.text))
                add_data(all_data, "RT_critics_count", make_int(re.sub(r"\W", "", counts[0].text)))
            else:
                add_data(all_data, "RT_critics_rating", "N/A")
                add_data(all_data, "RT_critics_count", "N/A")

            rt_users_data = s.find("div", {"class": "audience-score"})

            if rt_users_data:
                audience_score = rt_users_data.find("span", {"class": "mop-ratings-wrap__percentage"})
                if audience_score:
                    add_data(all_data, "RT_users_rating", remove_non_num(audience_score.text))
                else:
                    add_data(all_data, "RT_users_rating", "N/A")

                audience_count = rt_users_data.find("strong", {"class": "mop-ratings-wrap__text--small"})
                add_data(all_data, "RT_users_count", make_int(re.sub("[^0-9]", "", audience_count.text)))
            else:
                add_data(all_data, "RT_users_rating", "N/A")
                add_data(all_data, "RT_users_count", "N/A")
        else:
            add_data(all_data, "RT_critics_rating", "N/A")
            add_data(all_data, "RT_critics_count", "N/A")
            add_data(all_data, "RT_users_rating", "N/A")
            add_data(all_data, "RT_users_count", "N/A")
    else:
        add_data(all_data, "RT_critics_rating", "N/A")
        add_data(all_data, "RT_critics_count", "N/A")
        add_data(all_data, "RT_users_rating", "N/A")
        add_data(all_data, "RT_users_count", "N/A")

    add_data(all_data, "users",
             find_sum(all_data["IMDB_rating"], all_data["MC_users_rating"], all_data["RT_users_rating"]))
    add_data(all_data, "critics", find_sum(all_data["MC_critics_rating"], all_data["RT_critics_rating"]))

    print("done")

    return all_data


# print(movie_data("https://www.imdb.com/title/tt0076759"))
