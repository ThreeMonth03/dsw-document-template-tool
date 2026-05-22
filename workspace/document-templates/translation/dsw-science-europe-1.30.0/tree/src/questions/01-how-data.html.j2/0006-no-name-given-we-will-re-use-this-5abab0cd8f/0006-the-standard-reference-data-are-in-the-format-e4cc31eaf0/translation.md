# Translation Unit

- Source File: `src/questions/01-how-data.html.j2`
- Wrapper Name: `__tr_block_0005`
- Wrapper Order: `6`
- Wrapper Key: `no-name-given-we-will-re-use-this-5abab0cd8f`
- Unit Key: `the-standard-reference-data-are-in-the-format-e4cc31eaf0`
- Source Hash: `f4d43afbffaa4ddb93d945d48831d20283bd5f9c`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
The standard reference data are in the format that has to be transformed before using. / The standard reference data are in the format that does not have to be transformed and we can use it directly.
```

### Source (en)

~~~jinja
<p>
            {%- if refDataFormatReply == uuids.refDataFormatConvertAUuid -%}
              The standard reference data are in the format that has to be transformed before using.
            {%- elif refDataFormatReply == uuids.refDataFormatUseAUuid -%}
              The standard reference data are in the format that does not have to be transformed and we can use it directly.
            {% endif %}
~~~

### Translation (zh_Hant)

~~~jinja

~~~
