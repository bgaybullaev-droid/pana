"""Localized display names for listing parameters (AUTO-GENERATED).

DO NOT EDIT BY HAND. Regenerate with:
    python backend/scripts/gen_listing_i18n.py

Source of truth: frontend/src/shared/i18n/locales/{ru,uz-latn,uz-cyrl}/
{common,buyer}.json. This mirror lets backend-side text generation (AI
prompts + template fallback) emit the correct language/script per locale
instead of the raw storage keys (e.g. "olmazor" → "Алмазарский р-н").

Locale keys match the three AI-output locales: ru, uz (Latin), uz_cyrl.
"""

from __future__ import annotations

from typing import Optional

LOCALES = ("ru", "uz", "uz_cyrl")

REGION_NAMES: dict[str, dict[str, str]] = {
    "andijon": {"ru": "Андижанская обл.", "uz": "Andijon vil.", "uz_cyrl": "Андижон вил."},
    "buxoro": {"ru": "Бухарская обл.", "uz": "Buxoro vil.", "uz_cyrl": "Бухоро вил."},
    "fargona": {"ru": "Ферганская обл.", "uz": "Farg'ona vil.", "uz_cyrl": "Фарғона вил."},
    "jizzax": {"ru": "Джизакская обл.", "uz": "Jizzax vil.", "uz_cyrl": "Жиззах вил."},
    "namangan": {"ru": "Наманганская обл.", "uz": "Namangan vil.", "uz_cyrl": "Наманган вил."},
    "navoiy": {"ru": "Навоийская обл.", "uz": "Navoiy vil.", "uz_cyrl": "Навоий вил."},
    "qashqadaryo": {"ru": "Кашкадарьинская обл.", "uz": "Qashqadaryo vil.", "uz_cyrl": "Қашқадарё вил."},
    "qoraqalpogiston": {"ru": "Каракалпакстан", "uz": "Qoraqalpog'iston", "uz_cyrl": "Қорақалпоғистон"},
    "samarqand": {"ru": "Самаркандская обл.", "uz": "Samarqand vil.", "uz_cyrl": "Самарқанд вил."},
    "sirdaryo": {"ru": "Сырдарьинская обл.", "uz": "Sirdaryo vil.", "uz_cyrl": "Сирдарё вил."},
    "surxondaryo": {"ru": "Сурхандарьинская обл.", "uz": "Surxondaryo vil.", "uz_cyrl": "Сурхондарё вил."},
    "toshkent_shahri": {"ru": "Ташкент", "uz": "Toshkent", "uz_cyrl": "Тошкент"},
    "toshkent_viloyati": {"ru": "Ташкентская обл.", "uz": "Toshkent vil.", "uz_cyrl": "Тошкент вил."},
    "xorazm": {"ru": "Хорезмская обл.", "uz": "Xorazm vil.", "uz_cyrl": "Хоразм вил."},
}

DISTRICT_NAMES: dict[str, dict[str, str]] = {
    "amudaryo": {"ru": "Амударьинский р-н", "uz": "Amudaryo t.", "uz_cyrl": "Амударё т."},
    "andijon_sh": {"ru": "Андижан", "uz": "Andijon", "uz_cyrl": "Андижон"},
    "andijon_t": {"ru": "Андижанский р-н", "uz": "Andijon t.", "uz_cyrl": "Андижон т."},
    "angor": {"ru": "Ангорский р-н", "uz": "Angor t.", "uz_cyrl": "Ангор т."},
    "angren": {"ru": "Ангрен", "uz": "Angren", "uz_cyrl": "Ангрен"},
    "arnasoy": {"ru": "Арнасайский р-н", "uz": "Arnasoy t.", "uz_cyrl": "Арнасой т."},
    "asaka": {"ru": "Асакинский р-н", "uz": "Asaka t.", "uz_cyrl": "Асака т."},
    "baliqchi": {"ru": "Балыкчинский р-н", "uz": "Baliqchi t.", "uz_cyrl": "Балиқчи т."},
    "bandixon": {"ru": "Бандиханский р-н", "uz": "Bandixon t.", "uz_cyrl": "Бандихон т."},
    "baxmal": {"ru": "Бахмальский р-н", "uz": "Baxmal t.", "uz_cyrl": "Бахмал т."},
    "bekobod": {"ru": "Бекабад", "uz": "Bekobod", "uz_cyrl": "Бекобод"},
    "bektemir": {"ru": "Бектемирский р-н", "uz": "Bektemir t.", "uz_cyrl": "Бектемир т."},
    "beruniy": {"ru": "Берунийский р-н", "uz": "Beruniy t.", "uz_cyrl": "Беруний т."},
    "beshariq": {"ru": "Бешарыкский р-н", "uz": "Beshariq t.", "uz_cyrl": "Бешариқ т."},
    "bo_ka": {"ru": "Букинский р-н", "uz": "Bo'ka t.", "uz_cyrl": "Бўка т."},
    "bo_stonliq": {"ru": "Бостанлыкский р-н", "uz": "Bo'stonliq t.", "uz_cyrl": "Бўстонлиқ т."},
    "bo_z": {"ru": "Бозский р-н", "uz": "Bo'z t.", "uz_cyrl": "Бўз т."},
    "bo_zatov": {"ru": "Бозатауский р-н", "uz": "Bo'zatov t.", "uz_cyrl": "Бўзатов т."},
    "bog_dod": {"ru": "Багдадский р-н", "uz": "Bog'dod t.", "uz_cyrl": "Боғдод т."},
    "bog_ot": {"ru": "Багатский р-н", "uz": "Bog'ot t.", "uz_cyrl": "Боғот т."},
    "boyovut": {"ru": "Баяутский р-н", "uz": "Boyovut t.", "uz_cyrl": "Боёвут т."},
    "boysun": {"ru": "Байсунский р-н", "uz": "Boysun t.", "uz_cyrl": "Бойсун т."},
    "buloqboshi": {"ru": "Булакбашинский р-н", "uz": "Buloqboshi t.", "uz_cyrl": "Булоқбоши т."},
    "bulung_ur": {"ru": "Булунгурский р-н", "uz": "Bulung'ur t.", "uz_cyrl": "Булунғур т."},
    "buxoro_sh": {"ru": "Бухара", "uz": "Buxoro", "uz_cyrl": "Бухоро"},
    "buxoro_t": {"ru": "Бухарский р-н", "uz": "Buxoro t.", "uz_cyrl": "Бухоро т."},
    "chilonzor": {"ru": "Чиланзарский р-н", "uz": "Chilonzor t.", "uz_cyrl": "Чилонзор т."},
    "chimboy": {"ru": "Чимбайский р-н", "uz": "Chimboy t.", "uz_cyrl": "Чимбой т."},
    "chinoz": {"ru": "Чиназский р-н", "uz": "Chinoz t.", "uz_cyrl": "Чиноз т."},
    "chirchiq": {"ru": "Чирчик", "uz": "Chirchiq", "uz_cyrl": "Чирчиқ"},
    "chiroqchi": {"ru": "Чиракчинский р-н", "uz": "Chiroqchi t.", "uz_cyrl": "Чироқчи т."},
    "chortoq": {"ru": "Чартакский р-н", "uz": "Chortoq t.", "uz_cyrl": "Чортоқ т."},
    "chust": {"ru": "Чустский р-н", "uz": "Chust t.", "uz_cyrl": "Чуст т."},
    "dang_ara": {"ru": "Дангаринский р-н", "uz": "Dang'ara t.", "uz_cyrl": "Данғара т."},
    "dehqonobod": {"ru": "Дехканабадский р-н", "uz": "Dehqonobod t.", "uz_cyrl": "Деҳқонобод т."},
    "denov": {"ru": "Денауский р-н", "uz": "Denov t.", "uz_cyrl": "Денов т."},
    "do_stlik": {"ru": "Дустликский р-н", "uz": "Do'stlik t.", "uz_cyrl": "Дўстлик т."},
    "ellikqala": {"ru": "Элликкалинский р-н", "uz": "Ellikqal'a t.", "uz_cyrl": "Элликқалъа т."},
    "fargona_sh": {"ru": "Фергана", "uz": "Farg'ona", "uz_cyrl": "Фарғона"},
    "fargona_t": {"ru": "Ферганский р-н", "uz": "Farg'ona t.", "uz_cyrl": "Фарғона т."},
    "forish": {"ru": "Фаришский р-н", "uz": "Forish t.", "uz_cyrl": "Фориш т."},
    "furqat": {"ru": "Фуркатский р-н", "uz": "Furqat t.", "uz_cyrl": "Фурқат т."},
    "g_allaorol": {"ru": "Галляаральский р-н", "uz": "G'allaorol t.", "uz_cyrl": "Ғаллаорол т."},
    "g_ijduvon": {"ru": "Гиждуванский р-н", "uz": "G'ijduvon t.", "uz_cyrl": "Ғиждувон т."},
    "g_uzor": {"ru": "Гузарский р-н", "uz": "G'uzor t.", "uz_cyrl": "Ғузор т."},
    "guliston_sh": {"ru": "Гулистан", "uz": "Guliston", "uz_cyrl": "Гулистон"},
    "guliston_t": {"ru": "Гулистанский р-н", "uz": "Guliston t.", "uz_cyrl": "Гулистон т."},
    "gurlan": {"ru": "Гурленский р-н", "uz": "Gurlan t.", "uz_cyrl": "Гурлан т."},
    "hovos": {"ru": "Хавастский р-н", "uz": "Hovos t.", "uz_cyrl": "Ҳовос т."},
    "ishtixon": {"ru": "Иштыханский р-н", "uz": "Ishtixon t.", "uz_cyrl": "Иштихон т."},
    "izboskan": {"ru": "Избасканский р-н", "uz": "Izboskan t.", "uz_cyrl": "Избоскан т."},
    "jalaquduq": {"ru": "Джалакудукский р-н", "uz": "Jalaquduq t.", "uz_cyrl": "Жалақудуқ т."},
    "jarqo_rg_on": {"ru": "Джаркурганский р-н", "uz": "Jarqo'rg'on t.", "uz_cyrl": "Жарқўрғон т."},
    "jizzax_sh": {"ru": "Джизак", "uz": "Jizzax", "uz_cyrl": "Жиззах"},
    "jomboy": {"ru": "Джамбайский р-н", "uz": "Jomboy t.", "uz_cyrl": "Жомбой т."},
    "jondor": {"ru": "Жондорский р-н", "uz": "Jondor t.", "uz_cyrl": "Жондор т."},
    "karmana": {"ru": "Карманинский р-н", "uz": "Karmana t.", "uz_cyrl": "Кармана т."},
    "kasbi": {"ru": "Касбийский р-н", "uz": "Kasbi t.", "uz_cyrl": "Касби т."},
    "kattaqo_rg_on": {"ru": "Каттакурганский р-н", "uz": "Kattaqo'rg'on t.", "uz_cyrl": "Каттақўрғон т."},
    "kegeyli": {"ru": "Кегейлийский р-н", "uz": "Kegeyli t.", "uz_cyrl": "Кегейли т."},
    "kitob": {"ru": "Китабский р-н", "uz": "Kitob t.", "uz_cyrl": "Китоб т."},
    "ko_kdala": {"ru": "Кукдалинский р-н", "uz": "Ko'kdala t.", "uz_cyrl": "Кўкдала т."},
    "kogon": {"ru": "Каганский р-н", "uz": "Kogon t.", "uz_cyrl": "Когон т."},
    "konimex": {"ru": "Конимехский р-н", "uz": "Konimex t.", "uz_cyrl": "Конимех т."},
    "kosonsoy": {"ru": "Касансайский р-н", "uz": "Kosonsoy t.", "uz_cyrl": "Косонсой т."},
    "marg_ilon": {"ru": "Маргилан", "uz": "Marg'ilon", "uz_cyrl": "Марғилон"},
    "marhamat": {"ru": "Мархаматский р-н", "uz": "Marhamat t.", "uz_cyrl": "Марҳамат т."},
    "mingbuloq": {"ru": "Мингбулакский р-н", "uz": "Mingbuloq t.", "uz_cyrl": "Мингбулоқ т."},
    "mirishkor": {"ru": "Миришкорский р-н", "uz": "Mirishkor t.", "uz_cyrl": "Миришкор т."},
    "mirobod": {"ru": "Мирабадский р-н", "uz": "Mirobod t.", "uz_cyrl": "Миробод т."},
    "mirzacho_l": {"ru": "Мирзачульский р-н", "uz": "Mirzacho'l t.", "uz_cyrl": "Мирзачўл т."},
    "mirzaobod": {"ru": "Мирзаабадский р-н", "uz": "Mirzaobod t.", "uz_cyrl": "Мирзаобод т."},
    "mirzo_ulugbek": {"ru": "Мирзо-Улугбекский р-н", "uz": "Mirzo Ulug'bek t.", "uz_cyrl": "Мирзо Улуғбек т."},
    "moynaq": {"ru": "Муйнакский р-н", "uz": "Mo'ynaq t.", "uz_cyrl": "Мўйноқ т."},
    "muborak": {"ru": "Мубарекский р-н", "uz": "Muborak t.", "uz_cyrl": "Муборак т."},
    "muzrabod": {"ru": "Музрабадский р-н", "uz": "Muzrabod t.", "uz_cyrl": "Музробод т."},
    "namangan_sh": {"ru": "Наманган", "uz": "Namangan", "uz_cyrl": "Наманган"},
    "namangan_t": {"ru": "Наманганский р-н", "uz": "Namangan t.", "uz_cyrl": "Наманган т."},
    "narpay": {"ru": "Нарпайский р-н", "uz": "Narpay t.", "uz_cyrl": "Нарпай т."},
    "navbahor": {"ru": "Навбахорский р-н", "uz": "Navbahor t.", "uz_cyrl": "Навбаҳор т."},
    "navoiy_sh": {"ru": "Навои", "uz": "Navoiy", "uz_cyrl": "Навоий"},
    "nishon": {"ru": "Нишанский р-н", "uz": "Nishon t.", "uz_cyrl": "Нишон т."},
    "norin": {"ru": "Наринский р-н", "uz": "Norin t.", "uz_cyrl": "Норин т."},
    "nukus_sh": {"ru": "Нукус", "uz": "Nukus", "uz_cyrl": "Нукус"},
    "nukus_t": {"ru": "Нукусский р-н", "uz": "Nukus t.", "uz_cyrl": "Нукус т."},
    "nurafshon": {"ru": "Нурафшон", "uz": "Nurafshon", "uz_cyrl": "Нурафшон"},
    "nurobod": {"ru": "Нурабадский р-н", "uz": "Nurobod t.", "uz_cyrl": "Нуробод т."},
    "nurota": {"ru": "Нуратинский р-н", "uz": "Nurota t.", "uz_cyrl": "Нурота т."},
    "o_rtachirchiq": {"ru": "Среднечирчикский р-н", "uz": "O'rtachirchiq t.", "uz_cyrl": "Ўртачирчиқ т."},
    "o_zbekiston": {"ru": "Узбекистанский р-н", "uz": "O'zbekiston t.", "uz_cyrl": "Ўзбекистон т."},
    "ohangaron": {"ru": "Оханагарон", "uz": "Ohangaron", "uz_cyrl": "Оҳангарон"},
    "olmaliq": {"ru": "Олмалик", "uz": "Olmaliq", "uz_cyrl": "Олмалиқ"},
    "olmazor": {"ru": "Алмазарский р-н", "uz": "Olmazor t.", "uz_cyrl": "Олмазор т."},
    "olot": {"ru": "Олотский р-н", "uz": "Olot t.", "uz_cyrl": "Олот т."},
    "oltiariq": {"ru": "Алтыарыкский р-н", "uz": "Oltiariq t.", "uz_cyrl": "Олтиариқ т."},
    "oltinko_l": {"ru": "Алтынкульский р-н", "uz": "Oltinko'l t.", "uz_cyrl": "Олтинкўл т."},
    "oltinsoy": {"ru": "Алтынсайский р-н", "uz": "Oltinsoy t.", "uz_cyrl": "Олтинсой т."},
    "oqdaryo": {"ru": "Акдарьинский р-н", "uz": "Oqdaryo t.", "uz_cyrl": "Оқдарё т."},
    "oqoltin": {"ru": "Акалтынский р-н", "uz": "Oqoltin t.", "uz_cyrl": "Оқолтин т."},
    "oqqo_rg_on": {"ru": "Аккурганский р-н", "uz": "Oqqo'rg'on t.", "uz_cyrl": "Оққўрғон т."},
    "parkent": {"ru": "Паркентский р-н", "uz": "Parkent t.", "uz_cyrl": "Паркент т."},
    "pastdarg_om": {"ru": "Пастдаргомский р-н", "uz": "Pastdarg'om t.", "uz_cyrl": "Пастдарғом т."},
    "paxtachi": {"ru": "Пахтачийский р-н", "uz": "Paxtachi t.", "uz_cyrl": "Пахтачи т."},
    "paxtakor": {"ru": "Пахтакорский р-н", "uz": "Paxtakor t.", "uz_cyrl": "Пахтакор т."},
    "paxtaobod": {"ru": "Пахтаабадский р-н", "uz": "Paxtaobod t.", "uz_cyrl": "Пахтаобод т."},
    "payariq": {"ru": "Пайарыкский р-н", "uz": "Payariq t.", "uz_cyrl": "Паяриқ т."},
    "peshku": {"ru": "Пешкунский р-н", "uz": "Peshku t.", "uz_cyrl": "Пешку т."},
    "piskent": {"ru": "Пскентский р-н", "uz": "Piskent t.", "uz_cyrl": "Пискент т."},
    "pop": {"ru": "Папский р-н", "uz": "Pop t.", "uz_cyrl": "Поп т."},
    "qamashi": {"ru": "Камашинский р-н", "uz": "Qamashi t.", "uz_cyrl": "Қамаши т."},
    "qanliko_l": {"ru": "Канликульский р-н", "uz": "Qanliko'l t.", "uz_cyrl": "Қанликўл т."},
    "qarshi_sh": {"ru": "Карши", "uz": "Qarshi", "uz_cyrl": "Қарши"},
    "qarshi_t": {"ru": "Каршинский р-н", "uz": "Qarshi t.", "uz_cyrl": "Қарши т."},
    "qibray": {"ru": "Кибрайский р-н", "uz": "Qibray t.", "uz_cyrl": "Қибрай т."},
    "qiziltepa": {"ru": "Кызылтепинский р-н", "uz": "Qiziltepa t.", "uz_cyrl": "Қизилтепа т."},
    "qiziriq": {"ru": "Кизирикский р-н", "uz": "Qiziriq t.", "uz_cyrl": "Қизириқ т."},
    "qo_ng_irot": {"ru": "Кунградский р-н", "uz": "Qo'ng'irot t.", "uz_cyrl": "Қўнғирот т."},
    "qo_rg_ontepa": {"ru": "Кургантепинский р-н", "uz": "Qo'rg'ontepa t.", "uz_cyrl": "Қўрғонтепа т."},
    "qo_shko_pir": {"ru": "Кушкупырский р-н", "uz": "Qo'shko'pir t.", "uz_cyrl": "Қўшкўпир т."},
    "qo_shtepa": {"ru": "Куштепинский р-н", "uz": "Qo'shtepa t.", "uz_cyrl": "Қўштепа т."},
    "qorako_l": {"ru": "Каракульский р-н", "uz": "Qorako'l t.", "uz_cyrl": "Қоракўл т."},
    "qorao_zak": {"ru": "Караузякский р-н", "uz": "Qorao'zak t.", "uz_cyrl": "Қораўзак т."},
    "qorovulbozor": {"ru": "Каровулбазарский р-н", "uz": "Qorovulbozor t.", "uz_cyrl": "Қоровулбозор т."},
    "qumqo_rg_on": {"ru": "Кумкурганский р-н", "uz": "Qumqo'rg'on t.", "uz_cyrl": "Қумқўрғон т."},
    "quva": {"ru": "Кувинский р-н", "uz": "Quva t.", "uz_cyrl": "Қува т."},
    "quvasoy": {"ru": "Кувасай", "uz": "Quvasoy", "uz_cyrl": "Қувасой"},
    "quyi_chirchiq": {"ru": "Нижнечирчикский р-н", "uz": "Quyi chirchiq t.", "uz_cyrl": "Қуйи Чирчиқ т."},
    "rishton": {"ru": "Риштанский р-н", "uz": "Rishton t.", "uz_cyrl": "Риштон т."},
    "romitan": {"ru": "Ромитанский р-н", "uz": "Romitan t.", "uz_cyrl": "Ромитан т."},
    "samarqand_sh": {"ru": "Самарканд", "uz": "Samarqand", "uz_cyrl": "Самарқанд"},
    "samarqand_t": {"ru": "Самаркандский р-н", "uz": "Samarqand t.", "uz_cyrl": "Самарқанд т."},
    "sardoba": {"ru": "Сардобинский р-н", "uz": "Sardoba t.", "uz_cyrl": "Сардоба т."},
    "sariosiyo": {"ru": "Сариасийский р-н", "uz": "Sariosiyo t.", "uz_cyrl": "Сариосиё т."},
    "sayxunobod": {"ru": "Сайхунабадский р-н", "uz": "Sayxunobod t.", "uz_cyrl": "Сайхунобод т."},
    "sergeli": {"ru": "Сергелийский р-н", "uz": "Sergeli t.", "uz_cyrl": "Сергели т."},
    "shahrisabz": {"ru": "Шахрисабзский р-н", "uz": "Shahrisabz t.", "uz_cyrl": "Шаҳрисабз т."},
    "shahrixon": {"ru": "Шахриханский р-н", "uz": "Shahrixon t.", "uz_cyrl": "Шаҳрихон т."},
    "sharof_rashidov": {"ru": "Шараф-Рашидовский р-н", "uz": "Sharof Rashidov t.", "uz_cyrl": "Шароф Рашидов т."},
    "shayxontohur": {"ru": "Шайхантахурский р-н", "uz": "Shayxontohur t.", "uz_cyrl": "Шайхонтоҳур т."},
    "sherobod": {"ru": "Шерабадский р-н", "uz": "Sherobod t.", "uz_cyrl": "Шеробод т."},
    "sho_rchi": {"ru": "Шурчинский р-н", "uz": "Sho'rchi t.", "uz_cyrl": "Шўрчи т."},
    "shofirkon": {"ru": "Шафирканский р-н", "uz": "Shofirkon t.", "uz_cyrl": "Шофиркон т."},
    "shovot": {"ru": "Шаватский р-н", "uz": "Shovot t.", "uz_cyrl": "Шовот т."},
    "shumanay": {"ru": "Шуманайский р-н", "uz": "Shumanay t.", "uz_cyrl": "Шуманай т."},
    "sirdaryo_t": {"ru": "Сырдарьинский р-н", "uz": "Sirdaryo t.", "uz_cyrl": "Сирдарё т."},
    "so_x": {"ru": "Сохский р-н", "uz": "So'x t.", "uz_cyrl": "Сўх т."},
    "taxtako_pir": {"ru": "Тахтакупырский р-н", "uz": "Taxtako'pir t.", "uz_cyrl": "Тахтакўпир т."},
    "termiz_sh": {"ru": "Термез", "uz": "Termiz", "uz_cyrl": "Термиз"},
    "termiz_t": {"ru": "Термезский р-н", "uz": "Termiz t.", "uz_cyrl": "Термиз т."},
    "to_raqo_rg_on": {"ru": "Туракурганский р-н", "uz": "To'raqo'rg'on t.", "uz_cyrl": "Тўрақўрғон т."},
    "to_rtko_l": {"ru": "Турткульский р-н", "uz": "To'rtko'l t.", "uz_cyrl": "Тўрткўл т."},
    "tomdi": {"ru": "Тамдынский р-н", "uz": "Tomdi t.", "uz_cyrl": "Томди т."},
    "toshkent_t": {"ru": "Ташкентский р-н", "uz": "Toshkent t.", "uz_cyrl": "Тошкент т."},
    "toshloq": {"ru": "Ташлакский р-н", "uz": "Toshloq t.", "uz_cyrl": "Тошлоқ т."},
    "toyloq": {"ru": "Тайлакский р-н", "uz": "Toyloq t.", "uz_cyrl": "Тойлоқ т."},
    "tuproqqala": {"ru": "Тупраккалинский р-н", "uz": "Tuproqqal'a t.", "uz_cyrl": "Тупроққалъа т."},
    "uchko_prik": {"ru": "Учкуприкский р-н", "uz": "Uchko'prik t.", "uz_cyrl": "Учкўприк т."},
    "uchqo_rg_on": {"ru": "Учкурганский р-н", "uz": "Uchqo'rg'on t.", "uz_cyrl": "Учқўрғон т."},
    "uchquduq": {"ru": "Учкудукский р-н", "uz": "Uchquduq t.", "uz_cyrl": "Учқудуқ т."},
    "uchtepa": {"ru": "Учтепинский р-н", "uz": "Uchtepa t.", "uz_cyrl": "Учтепа т."},
    "ulug_nor": {"ru": "Улугнорский р-н", "uz": "Ulug'nor t.", "uz_cyrl": "Улуғнор т."},
    "urganch_sh": {"ru": "Ургенч", "uz": "Urganch", "uz_cyrl": "Урганч"},
    "urganch_t": {"ru": "Ургенчский р-н", "uz": "Urganch t.", "uz_cyrl": "Урганч т."},
    "urgut": {"ru": "Ургутский р-н", "uz": "Urgut t.", "uz_cyrl": "Ургут т."},
    "uychi": {"ru": "Уйчинский р-н", "uz": "Uychi t.", "uz_cyrl": "Уйчи т."},
    "uzun": {"ru": "Узунский р-н", "uz": "Uzun t.", "uz_cyrl": "Узун т."},
    "vobkent": {"ru": "Вабкентский р-н", "uz": "Vobkent t.", "uz_cyrl": "Вобкент т."},
    "xatirchi": {"ru": "Хатырчинский р-н", "uz": "Xatirchi t.", "uz_cyrl": "Хатирчи т."},
    "xazorasp": {"ru": "Хазараспский р-н", "uz": "Xazorasp t.", "uz_cyrl": "Хазорасп т."},
    "xiva": {"ru": "Хивинский р-н", "uz": "Xiva t.", "uz_cyrl": "Хива т."},
    "xo_jaobod": {"ru": "Ходжаабадский р-н", "uz": "Xo'jaobod t.", "uz_cyrl": "Хўжаобод т."},
    "xo_jayli": {"ru": "Ходжейлийский р-н", "uz": "Xo'jayli t.", "uz_cyrl": "Хўжайли т."},
    "xonobod": {"ru": "Ханабадский р-н", "uz": "Xonobod t.", "uz_cyrl": "Хонобод т."},
    "xonqa": {"ru": "Ханкинский р-н", "uz": "Xonqa t.", "uz_cyrl": "Хонқа т."},
    "yakkabog_": {"ru": "Яккабагский р-н", "uz": "Yakkabog' t.", "uz_cyrl": "Яккабоғ т."},
    "yakkasaroy": {"ru": "Яккасарайский р-н", "uz": "Yakkasaroy t.", "uz_cyrl": "Яккасарой т."},
    "yangiariq": {"ru": "Янгиарыкский р-н", "uz": "Yangiariq t.", "uz_cyrl": "Янгиариқ т."},
    "yangibozor": {"ru": "Янгибазарский р-н", "uz": "Yangibozor t.", "uz_cyrl": "Янгибозор т."},
    "yangihayot": {"ru": "Янгихаётский р-н", "uz": "Yangihayot t.", "uz_cyrl": "Янгиҳаёт т."},
    "yangiobod": {"ru": "Янгиободский р-н", "uz": "Yangiobod t.", "uz_cyrl": "Янгиобод т."},
    "yangiqo_rg_on": {"ru": "Янгикурганский р-н", "uz": "Yangiqo'rg'on t.", "uz_cyrl": "Янгиқўрғон т."},
    "yangiyo_l": {"ru": "Янгиюль", "uz": "Yangiyo'l", "uz_cyrl": "Янгийўл"},
    "yashnobod": {"ru": "Яшнабадский р-н", "uz": "Yashnobod t.", "uz_cyrl": "Яшнобод т."},
    "yozyovon": {"ru": "Язъяванский р-н", "uz": "Yozyovon t.", "uz_cyrl": "Ёзёвон т."},
    "yunusobod": {"ru": "Юнусабадский р-н", "uz": "Yunusobod t.", "uz_cyrl": "Юнусобод т."},
    "yuqorichirchiq": {"ru": "Верхнечирчикский р-н", "uz": "Yuqorichirchiq t.", "uz_cyrl": "Юқоричирчиқ т."},
    "zafarobod": {"ru": "Зафарабадский р-н", "uz": "Zafarobod t.", "uz_cyrl": "Зафаробод т."},
    "zangiota": {"ru": "Зангиатинский р-н", "uz": "Zangiota t.", "uz_cyrl": "Зангиота т."},
    "zarbdor": {"ru": "Зарбдорский р-н", "uz": "Zarbdor t.", "uz_cyrl": "Зарбдор т."},
    "zomin": {"ru": "Заминский р-н", "uz": "Zomin t.", "uz_cyrl": "Зомин т."},
}

PROPERTY_TYPE_NAMES: dict[str, dict[str, str]] = {
    "apartment": {"ru": "Квартира", "uz": "Kvartira", "uz_cyrl": "Квартира"},
    "house": {"ru": "Дом", "uz": "Uy", "uz_cyrl": "Уй"},
    "commercial": {"ru": "Коммерция", "uz": "Tijorat", "uz_cyrl": "Тижорат"},
    "land": {"ru": "Земля", "uz": "Yer", "uz_cyrl": "Ер"},
}

DEAL_TYPE_NAMES: dict[str, dict[str, str]] = {
    "sell": {"ru": "Продажа", "uz": "Sotish", "uz_cyrl": "Сотиш"},
    "rent": {"ru": "Аренда", "uz": "Ijara", "uz_cyrl": "Ижара"},
}

BUILDING_TYPE_NAMES: dict[str, dict[str, str]] = {
    "new": {"ru": "Новостройка", "uz": "Yangi bino", "uz_cyrl": "Янги бино"},
    "secondary": {"ru": "Вторичка", "uz": "Ikkilamchi", "uz_cyrl": "Иккиламчи"},
}

CONDITION_NAMES: dict[str, dict[str, str]] = {
    "euro": {"ru": "Евроремонт", "uz": "Yevroremont", "uz_cyrl": "Евроремонт"},
    "cosmetic": {"ru": "Косметический ремонт", "uz": "Kosmetik", "uz_cyrl": "Косметик таъмир"},
    "needs_repair": {"ru": "Без ремонта", "uz": "Ta'mir talab", "uz_cyrl": "Таъмирсиз"},
    "rough": {"ru": "Черновая отделка", "uz": "Qora suvoq", "uz_cyrl": "Қора сувоқ"},
}


def _lookup(table: dict[str, dict[str, str]], key: Optional[str], lang: str) -> str:
    """Localized name for a storage key; falls back to the raw key.

    Unknown keys (e.g. legacy crawler values not in the registry) return
    the key verbatim so we never crash a generation on a missing entry.
    """
    if not key:
        return ""
    entry = table.get(key)
    if entry is None:
        return key
    return entry.get(lang) or entry.get("ru") or key


def localize_region(key: Optional[str], lang: str) -> str:
    return _lookup(REGION_NAMES, key, lang)


def localize_district(key: Optional[str], lang: str) -> str:
    return _lookup(DISTRICT_NAMES, key, lang)


def localize_property_type(key: Optional[str], lang: str) -> str:
    return _lookup(PROPERTY_TYPE_NAMES, key, lang)


def localize_deal_type(key: Optional[str], lang: str) -> str:
    return _lookup(DEAL_TYPE_NAMES, key, lang)


def localize_building_type(key: Optional[str], lang: str) -> str:
    return _lookup(BUILDING_TYPE_NAMES, key, lang)


def localize_condition(key: Optional[str], lang: str) -> str:
    return _lookup(CONDITION_NAMES, key, lang)
