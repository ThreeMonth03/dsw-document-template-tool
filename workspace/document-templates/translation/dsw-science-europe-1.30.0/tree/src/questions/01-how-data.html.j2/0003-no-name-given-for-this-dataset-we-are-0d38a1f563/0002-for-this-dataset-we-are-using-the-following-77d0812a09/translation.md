# Translation Unit

- Source File: `src/questions/01-how-data.html.j2`
- Wrapper Name: `__tr_block_0002`
- Wrapper Order: `3`
- Wrapper Key: `no-name-given-for-this-dataset-we-are-0d38a1f563`
- Unit Key: `for-this-dataset-we-are-using-the-following-77d0812a09`
- Source Hash: `4fc7e7daa36985aa1661e527f1d35475a1ca0ad3`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
For this dataset, we are using the following instruments: {measuredDataInstrName} – {measuredDataInstrDesc}.
```

### Source (en)

~~~jinja
<p>For this dataset, we are using the following instruments:
              <ul>
                {%- for instrItem in measuredDataInstrItems -%}
                  {%- set instrPathPrefix = [measuredDataInstrPath, instrItem]|reply_path -%}
                  <li>
                    {%- set measuredDataInstrNamePath = [instrPathPrefix, uuids.measuredDataInstrNameQUuid]|reply_path -%}
                    {%- set measuredDataInstrName = repliesMap[measuredDataInstrNamePath]|reply_str_value -%}
                    {%- set measuredDataInstrDescPath = [instrPathPrefix, uuids.measuredDataInstrDescQUuid]|reply_path -%}
                    {%- set measuredDataInstrDesc = repliesMap[measuredDataInstrDescPath]|reply_str_value -%}
                    <strong>{{ measuredDataInstrName }}</strong>
                    {% if measuredDataInstrName and measuredDataInstrDesc -%}<span class="separator">&ndash;</span>{%- endif %}
                    {{ measuredDataInstrDesc }}
                  </li>
                {%- endfor -%}
~~~

### Translation (zh_Hant)

~~~jinja

~~~
