# Translation Unit

- Source File: `src/questions/01-how-data.html.j2`
- Wrapper Name: `__tr_block_0005`
- Wrapper Order: `6`
- Wrapper Key: `no-name-given-we-will-re-use-this-5abab0cd8f`
- Unit Key: `we-considered-reusing-this-standard-reference-data-available-b54461c96d`
- Source Hash: `35f16f113c8e476e8adabea3a753d2ab7134f2d7`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
We considered reusing this standard reference data available via: {refDataWhere}. / {refDataWhere}, but decided not to re-use it because it misses data we need / because it misses required aspects / because it is not sufficient quality / because its conditions of use do not allow us to use it / because: "{refDataUseNoOtherReasonReply}". /.
```

### Source (en)

~~~jinja
<p> We considered reusing this standard reference data
            {%- if refDataWhere -%}
            {{" "}}available via:{{" "}}
              {%- if refDataWhere.startswith("http://") or refDataWhere.startswith("https://") or refDataWhere.startswith("ftp://") -%}
                <a href="{{ refDataWhere }}" target="_blank">{{ refDataWhere }} </a>.
              {%- else -%}
                {{ refDataWhere}}
              {%- endif -%}
            {%- endif -%}

            {# no usage reason #}
            {%- if refDataUseNoReply -%}
              , but decided not to re-use it
              {%- if refDataUseNoReply == uuids.refDataUseNoDataAUuid -%}
                {{" "}}because it misses data we need
              {%- elif refDataUseNoReply == uuids.refDataUseNoAspectAUuid -%}
                {{" "}}because it misses required aspects
              {%- elif refDataUseNoReply == uuids.refDataUseNoQualityAUuid -%}
                {{" "}}because it is not sufficient quality
              {%- elif refDataUseNoReply == uuids.refDataUseNoCondAUuid -%}
                {{" "}}because its conditions of use do not allow us to use it
              {%- elif refDataUseNoReply == uuids.refDataUseNoReasonAUuid and refDataUseNoOtherReasonReply -%}
                {{" "}}because: "{{refDataUseNoOtherReasonReply}}"
              {%- endif -%}
              .
            {%- else -%}
            . </p>
            {%- endif -%}
~~~

### Translation (zh_Hant)

~~~jinja

~~~
