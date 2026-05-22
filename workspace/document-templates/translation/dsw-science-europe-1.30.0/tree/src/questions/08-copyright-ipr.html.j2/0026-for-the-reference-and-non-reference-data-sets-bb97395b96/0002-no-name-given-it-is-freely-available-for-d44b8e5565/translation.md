# Translation Unit

- Source File: `src/questions/08-copyright-ipr.html.j2`
- Wrapper Name: `__tr_block_0025`
- Wrapper Order: `26`
- Wrapper Key: `for-the-reference-and-non-reference-data-sets-bb97395b96`
- Unit Key: `no-name-given-it-is-freely-available-for-d44b8e5565`
- Source Hash: `9dac7d8f81f7bae3d3697fa0999fc17ab127f525`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
{refDataNameReply} / (no name given) It is freely available for any use (public domain or CC0). / It is freely available with obligation to quote the source (e.g. CC-BY). / It is available under specific restrictions, which we will follow in our project{value}
```

### Source (en)

~~~jinja
<li>
                {%- if refDataNameReply -%}
                  <div>{{ refDataNameReply }}</div>
                {%- else -%}
                  <div>(no name given)</div>
                {%- endif -%}
                
                {% if refDataConditionsAUuid == uuids.refDataConditionsCC0AUuid -%}
                  It is freely available for any use (public domain or CC0).
                {%- elif refDataConditionsAUuid == uuids.refDataConditionsCCBYAUuid -%}
                  It is freely available with obligation to quote the source (e.g. CC-BY).
                {%- elif refDataConditionsAUuid == uuids.refDataConditionsOtherAUuid -%}
                  {%- set refDataConditionsOtherPath = [refDataConditionsPath, uuids.refDataConditionsOtherAUuid, uuids.refDataConditionsOtherQUuid]|reply_path -%}
                  {%- set refDataConditionsOther = repliesMap[refDataConditionsOtherPath]|reply_str_value -%}
                  It is available under specific restrictions, which we will follow in our project{{ ": " ~ refDataConditionsOther|dot if refDataConditionsOther else "." }}
                {%- endif -%}
~~~

### Translation (zh_Hant)

~~~jinja

~~~
