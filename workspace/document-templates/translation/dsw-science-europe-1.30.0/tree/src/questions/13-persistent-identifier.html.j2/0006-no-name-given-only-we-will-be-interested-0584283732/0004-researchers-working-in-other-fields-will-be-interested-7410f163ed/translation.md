# Translation Unit

- Source File: `src/questions/13-persistent-identifier.html.j2`
- Wrapper Name: `__tr_block_0005`
- Wrapper Order: `6`
- Wrapper Key: `no-name-given-only-we-will-be-interested-0584283732`
- Unit Key: `researchers-working-in-other-fields-will-be-interested-7410f163ed`
- Source Hash: `5af4c8966808544569168bd54d63c80f1918172d`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
Researchers working in other fields will be interested in re-using this data because: {measuredDataReuseOtherFieldHowReply}. /.
```

### Source (en)

~~~jinja
<p>Researchers working in other fields will be interested in re-using this data
                
                {%- if measuredDataReuseOtherFieldHowReply -%}
                
                 {{" "}}because: {{measuredDataReuseOtherFieldHowReply|dot}}</p>
                {%- else -%}
                .
                {%- endif -%}
~~~

### Translation (zh_Hant)

~~~jinja

~~~
