# Translation Unit

- Source File: `src/questions/01-how-data.html.j2`
- Wrapper Name: `__tr_block_0005`
- Wrapper Order: `6`
- Wrapper Key: `no-name-given-we-will-re-use-this-5abab0cd8f`
- Unit Key: `this-standard-reference-data-will-be-available-for-76daf7f83c`
- Source Hash: `524a4367319e1a351ba8fd25a37e21e8f8a6ea24`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
This standard reference data will be available for long-term by the provider. / We will keep the copy of this standard reference data and make it available with our results. / This standard reference data will be available for long-term by the provider as well as we will keep the copy of this dataset and make it available with our results.
```

### Source (en)

~~~jinja
<p>
            {%- if refDataReproduceReply == uuids.refDataReproduceProviderAUuid -%}
              This standard reference data will be available for long-term by the provider.
            {%- elif refDataReproduceReply == uuids.refDataReproduceCopyAUuid  -%}
              We will keep the copy of this standard reference data and make it available with our results. 
            {%- elif refDataReproduceReply == uuids.refDataReproduceBothAUuid -%}
              This standard reference data will be available for long-term by the provider as well as we will keep the copy of this dataset and make it available with our results.
            {%- endif -%}
~~~

### Translation (zh_Hant)

~~~jinja

~~~
