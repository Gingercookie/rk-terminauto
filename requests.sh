# This represents a successful captcha solve request
curl 'https://service2.diplo.de/rktermin/extern/appointment_showMonth.do' \
    -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8' \
    -H 'Accept-Language: en-US,en;q=0.6' \
    -H 'Cache-Control: max-age=0' \
    -H 'Connection: keep-alive' \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    -b 'JSESSIONID=A758B6D17AC942904D714B61ED5E8878; KEKS=TERMINA' \
    -H 'Origin: https://service2.diplo.de' \
    -H 'Referer: https://service2.diplo.de/rktermin/extern/appointment_showMonth.do?locationCode=losa&realmId=1363&categoryId=3301&dateStr=01.08.2026' \
    -H 'Sec-Fetch-Dest: document' \
    -H 'Sec-Fetch-Mode: navigate' \
    -H 'Sec-Fetch-Site: same-origin' \
    -H 'Sec-Fetch-User: ?1' \
    -H 'Sec-GPC: 1' \
    -H 'Upgrade-Insecure-Requests: 1' \
    -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36' \
    -H 'sec-ch-ua: "Brave";v="149", "Chromium";v="149", "Not)A;Brand";v="24"' \
    -H 'sec-ch-ua-mobile: ?0' \
    -H 'sec-ch-ua-platform: "macOS"' \
    --data-raw 'captchaText=8xya7a&rebooking=&token=&lastname=&firstname=&email=&locationCode=losa&realmId=1363&categoryId=3301&openingPeriodId=&date=01.08.2026&dateStr=01.08.2026&action%3Aappointment_showMonth=Continue'

# This represents an already-authorized session just searching for available appointments
curl 'https://service2.diplo.de/rktermin/extern/appointment_showMonth.do?locationCode=losa&realmId=1363&categoryId=3301' \
    -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8' \
    -H 'Accept-Language: en-US,en;q=0.6' \
    -H 'Cache-Control: no-cache' \
    -H 'Connection: keep-alive' \
    -b 'JSESSIONID=4CFE38051CCC3134C020FE01EA8D14D2; KEKS=TERMINA' \
    -H 'Pragma: no-cache' \
    -H 'Referer: https://service2.diplo.de/rktermin/extern/choose_category.do?locationCode=losa&realmId=1363&categoryId=3301' \
    -H 'Sec-Fetch-Dest: document' \
    -H 'Sec-Fetch-Mode: navigate' \
    -H 'Sec-Fetch-Site: same-origin' \
    -H 'Sec-Fetch-User: ?1' \
    -H 'Sec-GPC: 1' \
    -H 'Upgrade-Insecure-Requests: 1' \
    -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36' \
    -H 'sec-ch-ua: "Brave";v="149", "Chromium";v="149", "Not)A;Brand";v="24"' \
    -H 'sec-ch-ua-mobile: ?0' \
    -H 'sec-ch-ua-platform: "macOS"'
