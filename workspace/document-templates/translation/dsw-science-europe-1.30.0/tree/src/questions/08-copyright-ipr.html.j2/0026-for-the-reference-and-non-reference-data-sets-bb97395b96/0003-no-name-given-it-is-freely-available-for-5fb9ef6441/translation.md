# Translation Unit

- Source File: `src/questions/08-copyright-ipr.html.j2`
- Wrapper Name: `__tr_block_0025`
- Wrapper Order: `26`
- Wrapper Key: `for-the-reference-and-non-reference-data-sets-bb97395b96`
- Unit Key: `no-name-given-it-is-freely-available-for-5fb9ef6441`
- Source Hash: `284d17669a7d6ecf686fe64ee16b4a63567b5f11`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
{nrefDataNameReply} / (no name given) It is freely available for any use (public domain or CC0). / It is freely available with obligation to quote the source (e.g. CC-BY). / It is available under specific restrictions, which we will follow in our project{value}
```

### Source (en)

~~~jinja
<li>
                {%- if nrefDataNameReply -%}
                  <div>{{ nrefDataNameReply }}</div>
                {%- else -%}
                  <div>(no name given)</div>
                {%- endif -%}
                {% if nrefDataConditionsAUuid == uuids.nrefDataConditionsCC0AUuid -%}
                  It is freely available for any use (public domain or CC0).
                {%- elif nrefDataConditionsAUuid == uuids.nrefDataConditionsCCBYAUuid -%}
                  It is freely available with obligation to quote the source (e.g. CC-BY).
                {%- elif nrefDataConditionsAUuid == uuids.nrefDataConditionsOtherAUuid -%}
                  {%- set nrefDataConditionsOtherPath = [nrefDataConditionsPath, uuids.nrefDataConditionsOtherAUuid, uuids.refDataConditionsOtherQUuid]|reply_path -%}
                  {%- set nrefDataConditionsOther = repliesMap[nrefDataConditionsOtherPath]|reply_str_value -%}
                  It is available under specific restrictions, which we will follow in our project{{ ": " ~ nrefDataConditionsOther|dot if nrefDataConditionsOther else "." }}
                {%- endif -%}
~~~

### Translation (zh_Hant)

~~~jinja

~~~
