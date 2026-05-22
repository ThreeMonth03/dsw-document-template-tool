# Translation Unit

- Source File: `src/questions/01-how-data.html.j2`
- Wrapper Name: `__tr_block_0005`
- Wrapper Order: `6`
- Wrapper Key: `no-name-given-we-will-re-use-this-5abab0cd8f`
- Unit Key: `this-standard-reference-data-are-freely-available-for-efb271512c`
- Source Hash: `ebd4e5703f458d6793342b5249d931f0595a1dfd`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
This standard reference data are{value} freely available for any use. / freely available with obligation to quote the source. / available with following restrictions: "{refDataConditionsOtherRepl}". / restrictions, that will be specified.
```

### Source (en)

~~~jinja
<p>This standard reference data are{{+" "}}
              {%- if refDataConditionsReply == uuids.refDataConditionsCC0AUuid -%}
                freely available for any use.
              {%- elif refDataConditionsReply == uuids.refDataConditionsCCBYAUuid -%}
                freely available with obligation to quote the source.
              {%- elif refDataConditionsReply == uuids.refDataConditionsOtherAUuid -%}
                available with {{" "}}
                  {%- if refDataConditionsOtherRepl -%}
                    following restrictions: "{{refDataConditionsOtherRepl}}".
                  {%- else -%}
                    {{" "}}restrictions, that will be specified.
                  {%- endif -%}
              {%- endif -%}
~~~

### Translation (zh_Hant)

~~~jinja

~~~
