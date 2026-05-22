# Translation Unit

- Source File: `src/questions/01-how-data.html.j2`
- Wrapper Name: `__tr_block_0006`
- Wrapper Order: `7`
- Wrapper Key: `no-name-given-we-will-re-use-this-6759c9c657`
- Unit Key: `we-will-re-use-this-non-referece-data-5096cc98db`
- Source Hash: `ae68d709575134df4958725c463f6147603f5629`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
We will re-use this non-referece data available via: {nrefDataWhere}. / {nrefDataWhere} {value}in order to "{nrefDataUsageReply}".
```

### Source (en)

~~~jinja
<p>We will re-use this non-referece data 
          {%- if nrefDataWhere -%}
         {{" "}} available via:{{" "}}
            {%- if nrefDataWhere.startswith("http://") or nrefDataWhere.startswith("https://") or nrefDataWhere.startswith("ftp://") -%}
              <a href="{{ nrefDataWhere }}" target="_blank">{{ nrefDataWhere }} </a>.
            {%- else -%}
              {{ nrefDataWhere }}
            {%- endif -%}
          {%- endif -%}
    
          {# usage #}
          {%- set nrefDataUsageQ = [nrefDataUsedPrefix, uuids.nrefDataUsageQUuid]|reply_path  -%}
          {%- set nrefDataUsageReply = repliesMap[nrefDataUsageQ]|reply_str_value -%}
          {%- if nrefDataUsageReply -%}
            {{+" "}}in order to "{{ nrefDataUsageReply}}"
          {%- endif -%}
          .</p>
~~~

### Translation (zh_Hant)

~~~jinja

~~~
