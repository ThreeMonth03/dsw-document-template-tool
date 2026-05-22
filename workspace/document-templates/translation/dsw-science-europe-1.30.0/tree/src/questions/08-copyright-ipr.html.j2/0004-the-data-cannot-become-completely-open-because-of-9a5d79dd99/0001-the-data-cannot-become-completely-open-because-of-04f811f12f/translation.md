# Translation Unit

- Source File: `src/questions/08-copyright-ipr.html.j2`
- Wrapper Name: `__tr_block_0003`
- Wrapper Order: `4`
- Wrapper Key: `the-data-cannot-become-completely-open-because-of-9a5d79dd99`
- Unit Key: `the-data-cannot-become-completely-open-because-of-04f811f12f`
- Source Hash: `05a6a906f462cc428deb0a9059494d0a17129853`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
The data cannot become completely open because of legal reasons. / of patent-related business reasons. / of non-patent business reasons{value} / we want to publish a paper first. / we have other than paper-publishing reasons{value} / of:
```

### Source (en)

~~~jinja
The data cannot become completely open because 
        {%- if nReasons == 1 -%}
          {%- if legalReasons %}
            of legal reasons.
          {%- elif businessReasonsPatents %}
            of patent-related business reasons.
          {%- elif businessReasonsOther %}
            of non-patent business reasons{{  ": " ~ notOpenBusinessReasonsOther|dot if notOpenBusinessReasonsOther else "." }}
          {%- elif otherReasonsPapers %}
            we want to publish a paper first.
          {%- elif otherReasonsOther %}
            we have other than paper-publishing reasons{{ ": " ~ notOpenOtherReasonsOther|dot if notOpenOtherReasonsOther else "." }}
          {%- endif -%}
        {%- else %}
          of:
~~~

### Translation (zh_Hant)

~~~jinja

~~~
