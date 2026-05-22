# Translation Unit

- Source File: `src/questions/01-how-data.html.j2`
- Wrapper Name: `__tr_block_0005`
- Wrapper Order: `6`
- Wrapper Key: `no-name-given-we-will-re-use-this-5abab0cd8f`
- Unit Key: `we-will-re-use-this-standard-reference-data-d5c0e81a8f`
- Source Hash: `46765be94a4a9f4a6ff6bbc998e3e8a2b57e8c18`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
We will re-use this standard reference data available via: {refDataWhere}. / {refDataWhere} {value}in order to "{refDataUsageReply}".
```

### Source (en)

~~~jinja
<p>We will re-use this standard reference data
            {%- if refDataWhere -%}
              {{" "}}available via:{{" "}}
              {%- if refDataWhere.startswith("http://") or refDataWhere.startswith("https://") or refDataWhere.startswith("ftp://") -%}
                <a href="{{ refDataWhere }}" target="_blank">{{ refDataWhere }} </a>.
              {%- else -%}
                {{ refDataWhere }}
             {%- endif -%}
            {%- endif -%}
    
            {# usage #}
            {%- set refDataUsageQ = [ refDataUsedPrefix, uuids.refDataUsageQUuid]|reply_path -%}
            {%- set refDataUsageReply = repliesMap[refDataUsageQ]|reply_str_value  -%}
            {%- if refDataUsageReply -%}
                {{+" "}}in order to "{{ refDataUsageReply}}"
            {%- endif -%}
            .</p>
~~~

### Translation (zh_Hant)

~~~jinja

~~~
