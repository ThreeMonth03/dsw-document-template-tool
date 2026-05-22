# Translation Unit

- Source File: `src/questions/01-how-data.html.j2`
- Wrapper Name: `__tr_block_0006`
- Wrapper Order: `7`
- Wrapper Key: `no-name-given-we-will-re-use-this-6759c9c657`
- Unit Key: `this-data-are-fixed-therefore-will-not-influence-e9747c3a75`
- Source Hash: `25071ddc27df6ba08dbf15075a54b44aa0a2f913`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
This data{value} are fixed, therefore will not influence reproducibility of our results. / may change in the future, which might influence reproducibility of our results.
```

### Source (en)

~~~jinja
<p>This data{{+" "}}
            {%- if nrefDataFixedReply == uuids.nrefDataFixedFixedAUuid -%}
              are fixed, therefore will not influence reproducibility of our results.
            {%- elif nrefDataFixedReply == uuids.nrefDataFixedChangeAUuid -%}
              may change in the future, which might influence reproducibility of our results.
            {%- endif -%}
~~~

### Translation (zh_Hant)

~~~jinja

~~~
