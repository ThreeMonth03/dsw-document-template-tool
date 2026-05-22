# Translation Unit

- Source File: `src/questions/01-how-data.html.j2`
- Wrapper Name: `__tr_block_0006`
- Wrapper Order: `7`
- Wrapper Key: `no-name-given-we-will-re-use-this-6759c9c657`
- Unit Key: `we-will-use-the-complete-data-set-only-e7e4f8ac1b`
- Source Hash: `71c1fba6574323f7f0def26e37aee17c326146cf`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
We will use{value} the complete data set. / only subset of data and we will select it by filtering and/or selection (which will be documented). / only selected subset of data, which will be available together with our results.
```

### Source (en)

~~~jinja
<p>We will use{{+" "}}
            {%- if nrefDataCompleteReply == uuids.nrefDataCompleteUseAUuid -%}
              the complete data set. 
            {%- elif nrefDataCompleteReply == uuids.nrefDataCompleteDocumentAUuid -%}
              only subset of data and we will select it by filtering and/or selection (which will be documented).
            {%- elif nrefDataCompleteReply == uuids.nrefDataCompleteSubsetAUuid -%}
              only selected subset of data, which will be available together with our results.
            {%- endif -%}
~~~

### Translation (zh_Hant)

~~~jinja

~~~
