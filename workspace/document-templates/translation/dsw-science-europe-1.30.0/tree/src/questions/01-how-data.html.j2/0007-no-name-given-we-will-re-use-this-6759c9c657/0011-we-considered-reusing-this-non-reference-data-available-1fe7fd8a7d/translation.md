# Translation Unit

- Source File: `src/questions/01-how-data.html.j2`
- Wrapper Name: `__tr_block_0006`
- Wrapper Order: `7`
- Wrapper Key: `no-name-given-we-will-re-use-this-6759c9c657`
- Unit Key: `we-considered-reusing-this-non-reference-data-available-1fe7fd8a7d`
- Source Hash: `446d5df839bed6e36cf05ee68eea8f80420f226e`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
We considered reusing this non-reference data {value}available via: {nrefDataWhere}. / {nrefDataWhere}, but decided not to reuse it because it misses data we need / becauseit misses required aspects / becauseit is not sufficient quality / because its conditions of use do not allow us to use it / because: "{nrefDataUseNoOtherReasonReply}". /.
```

### Source (en)

~~~jinja
<p>We considered reusing this non-reference data 
          {%- if nrefDataWhere -%}
          {{+" "}}available via:{{" "}}
            {%- if nrefDataWhere.startswith("http://") or nrefDataWhere.startswith("https://") or nrefDataWhere.startswith("ftp://") -%}
              <a href="{{ rnefDataWhere }}" target="_blank">{{ nrefDataWhere }} </a>.
            {%- else -%}
              {{ nrefDataWhere }}
            {%- endif -%}
          {%- endif -%}

          {# no usage reason #}
          {%- if nrefDataUseNoReply -%}
            , but decided not to reuse it
            {%- if nrefDataUseNoReply == uuids.nrefDataUseNoDataAUuid -%}
              {{" "}}because it misses data we need
            {%- elif nrefDataUseNoReply == uuids.nrefDataUseNoAspectAUuid -%}
              {{" "}}becauseit misses required aspects
            {%- elif nrefDataUseNoReply == uuids.nrefDataUseNoQualityAUuid -%}
              {{" "}}becauseit is not sufficient quality
            {%- elif nrefDataUseNoReply == uuids.nrefDataUseNoCondAUuid -%}
              {{" "}}because its conditions of use do not allow us to use it
            {%- elif nrefDataUseNoReply == uuids.nrefDataUseNoReasonAUuid and nrefDataUseNoOtherReasonReply -%}
              {{" "}}because: "{{nrefDataUseNoOtherReasonReply}}"
            {%- endif -%}
            .
          {%- else -%}
          .</p>
          {%- endif -%}
~~~

### Translation (zh_Hant)

~~~jinja

~~~
