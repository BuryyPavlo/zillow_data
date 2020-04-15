from lxml import html
from urllib.request import Request, urlopen
import requests
import unicodecsv as csv
import argparse
import json


def clean(text):
    if text:
        return ' '.join(' '.join(text).split())
    return None


def get_headers():
    # Creating headers.
    headers = {'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
               'accept-encoding': 'gzip, deflate, sdch, br',
               'accept-language': 'en-GB,en;q=0.8,en-US;q=0.6,ml;q=0.4',
               'cache-control': 'max-age=0',
               'upgrade-insecure-requests': '1',
               'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36'}
    return headers


def create_url(zipcode, filter,page):
    beds = "2"
    baths = '2.0'
    if filter == "newest":
        url = "https://www.zillow.com/homes/for_sale/{0}/houses/{2}-_beds/{3}-_baths/{1}_p/days_sort".format(zipcode,page,beds,baths)
    elif filter == "cheapest":
        url = "https://www.zillow.com/homes/for_sale/{0}/houses/{2}-_beds/{3}-_baths/{1}_p/0_singlestory/pricea_sort/".format(zipcode,page,beds,baths)
    else:
        url = "https://www.zillow.com/homes/for_sale/{0}/houses/{2}-_beds/{3}-_baths/{1}_p/0_singlestory/priced_sort/".format(zipcode,page,beds,baths)
    print(url)
    return url


def save_to_file(response):
    # saving response to `response.html`
    with open("response.html", 'w') as fp:
        fp.write(response.text)


def write_data_to_csv(data):
    # saving scraped data to csv.

    with open("properties-sale-%s.csv" % (zipcode), 'wb') as csvfile:
        fieldnames = ['id',
                'address',
                'city',
                'state',
                'postal_code',
                'price',
                'estimate',
                'taxAssessedValue',
                'beds',
                'bathrooms',
                'livingArea',
                'lotSize',
                'url',
                'title',
                'yearBuilt',
                'homeType',
                'sold']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in data:
            writer.writerow(row)


def get_response(url):
    # Getting response from zillow.com.
    for i in range(5):
        response = requests.get(url, headers=get_headers())
        print("status code received:", response.status_code)
        if response.status_code != 200:
            # saving response to file for debugging purpose.
            save_to_file(response)
            continue
        else:
            save_to_file(response)
            return response
    return None

def get_data_from_json(raw_json_data):
    # getting data from json (type 2 of their A/B testing page)
    #print(raw_json_data)
    cleaned_data = clean(raw_json_data).replace('<!--', "").replace("-->", "")
    properties_list = []

    try:
        json_data = json.loads(cleaned_data)
        search_results = json_data.get('searchResults').get('listResults', [])
        #print(search_results)

        for properties in search_results:
            id = properties.get('zpid')
            address = properties.get('addressStreet')

            property_url = properties.get('detailUrl')
            title = properties.get('statusText')
            datesold = properties.get('variableData',{}).get('text')

            property_info = properties.get('hdpData',{}).get('homeInfo',{})
            city = property_info.get('city')
            state = property_info.get('state')
            postal_code = property_info.get('zipcode')
            bedrooms = property_info.get('bedrooms')
            bathrooms = property_info.get('bathrooms')
            livingArea = property_info.get('livingArea')
            yearBuilt = property_info.get('yearBuilt')
            lotSize = property_info.get('lotSize')
            homeType = property_info.get('homeType')
            estimate = property_info.get('zestimate')
            price = property_info.get('priceForHDP')
            taxAssessedValue = property_info.get('taxAssessedValue')

            data = {'id': id,
                    'address': address,
                    'city': city,
                    'state': state,
                    'postal_code': postal_code,
                    'price': price,
                    'estimate':estimate,
                    'taxAssessedValue':taxAssessedValue,
                    'beds': bedrooms,
                    'bathrooms': bathrooms,
                    'livingArea': livingArea,
                    'lotSize':lotSize,
                    'url': property_url,
                    'title': title,
                    'yearBuilt':yearBuilt,
                    'homeType':homeType,
                    'sold':datesold}
            properties_list.append(data)
        #print(properties_list)
        return properties_list

    except ValueError:
        print("Invalid json")
        return None


def parse(zipcode, filter=None,page= 1):
    url = create_url(zipcode, filter,page)
    response = get_response(url)

    if not response:
        print("Failed to fetch the page, please check `response.html` to see the response received from zillow.com.")
        return None

    req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    webpage = urlopen(req).read()

    parser = html.fromstring(webpage)
    search_results = parser.xpath("//div[@id='search-results']//article")

    if not search_results:
        print("parsing from json data")
        # identified as type 2 page
        raw_json_data = parser.xpath('//script[@data-zrr-shared-data-key="mobileSearchPageStore"]//text()')
        return get_data_from_json(raw_json_data)



if __name__ == "__main__":
    # Reading arguments

    argparser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    argparser.add_argument('zipcode', help='')
    sortorder_help = """
    available sort orders are :
    newest : Latest property details,
    cheapest : Properties with cheapest price
    """

    argparser.add_argument('sort', nargs='?', help=sortorder_help, default='Homes For You')
    args = argparser.parse_args()
    zipcode = args.zipcode
    sort = args.sort
    print ("Fetching data for %s" % (zipcode))
    scraped_data = []
    for page in range(1,5): # pages 1-5
        scraped_data_page = parse(zipcode, sort,page)
        scraped_data = scraped_data+scraped_data_page
    #print(scraped_data)
    if scraped_data:
        print ("Writing data to output file")
        write_data_to_csv(scraped_data)
