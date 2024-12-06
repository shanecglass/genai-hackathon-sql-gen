```text
scg-l200-genai2.travel_chat.users JOIN scg-l200-genai2.travel_chat.user_airports ON user_id AND user_name
scg-l200-genai2.geo_us_boundaries.states JOIN scg-l200-genai2.travel_chat.users ON states.state = REGEXP_EXTRACT(users.user_location, r', ([A-Z]{2})$')
scg-l200-genai2.travel_chat.users LEFT JOIN scg-l200-genai2.geo_us_places.us_national_places ON places.state_fips_code = users.state_fips_code AND places.place_name = REGEXP_EXTRACT(users.user_location, r'^(.*), [A-Z]{2}$')
scg-l200-genai2.travel_chat.users JOIN scg-l200-genai2.geo_us_places.us_national_places ON users.user_name = "Abigail_Clark" AND places.place_id = "1836003"
scg-l200-genai2.thelook.order_items JOIN scg-l200-genai2.thelook.products ON order_items.product_id = products.id
scg-l200-genai2.thelook.order_items JOIN scg-l200-genai2.thelook.users ON order_items.user_id = users.id
scg-l200-genai2.travel_chat.user_airports JOIN  ON x.name = .airport
scg-l200-genai2.travel_chat.users JOIN scg-l200-genai2.faa.us_airports ON airports.service_city = REGEXP_EXTRACT(users.user_location, r'^(.*), [A-Z]{2}$')

```
