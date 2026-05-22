# Translation Unit

- Source File: `src/questions/01-how-data.html.j2`
- Wrapper Name: `__tr_block_0006`
- Wrapper Order: `7`
- Wrapper Key: `no-name-given-we-will-re-use-this-6759c9c657`
- Unit Key: `this-data-are-freely-available-for-any-use-d31f25eb91`
- Source Hash: `4251d67189b0b79cb353219f0d13f6a46c385370`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
This data are{value} freely available for any use. / freely available with obligation to quote the source. / available with following restrictions: "{nrefDataConditionsOtherReply}". / restrictions, that will be specified.
```

### Source (en)

~~~jinja
<p>This data are{{+" "}}
            {%- if nrefDataConditionsReply == uuids.nrefDataConditionsCC0AUuid -%}
              freely available for any use.
            {%- elif nrefDataConditionsReply == uuids.nrefDataConditionsCCBYAUuid -%}
              freely available with obligation to quote the source.
            {%- elif nrefDataConditionsReply == uuids.nrefDataConditionsOtherAUuid  -%}
              {%- set nrefDataConditionsOther = [nrefDataConditions, uuids.nrefDataConditionsOtherAUuid, uuids.nrefDataConditionsOtherQUuid]|reply_path -%}
              {%- set nrefDataConditionsOtherReply = repliesMap[nrefDataConditionsOther]|reply_str_value -%}
              {%- if nrefDataConditionsOtherReply -%}
                available with{{" "}}
                  {%- if nrefDataConditionsOtherReply -%}
                   following restrictions: "{{nrefDataConditionsOtherReply}}".
                  {%- else -%}
                    {{" "}}restrictions, that will be specified.
                  {%- endif -%}
              {%- endif -%}
            {%- endif -%}
~~~

### Translation (zh_Hant)

~~~jinja

~~~
