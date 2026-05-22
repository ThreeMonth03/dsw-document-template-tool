# Translation Unit

- Source File: `src/questions/03-docs-metadata.html.j2`
- Wrapper Name: `__tr_block_0012`
- Wrapper Order: `13`
- Wrapper Key: `metadata-will-be-openly-available-including-instructions-how-b8e0bab038`
- Unit Key: `metadata-will-be-openly-available-including-instructions-how-a15090bfee`
- Source Hash: `dff86a8751ff432c1f529fa9f36b5eef4afb3677`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
Metadata will be openly available including instructions how to get access to the data. / Metadata will be openly available without instructions how to get access to the data. / Metadata will be openly available. Metadata will not be available in a form that can be harvested and indexed. / Metadata will be available in a form that can be harvested and indexed (managed by the used repository / repositories). / Metadata will be available in a form that can be harvested and indexed.
```

### Source (en)

~~~jinja
{%- if metadataOpenInstrAUuid == uuids.metadataOpenInstrNoAUuid %}
        Metadata will be openly available including instructions how to get access to the data.
      {%- elif metadataOpenInstrAUuid == uuids.metadataOpenInstrNoAUuid %}
        Metadata will be openly available without instructions how to get access to the data.
      {%- else %}
        Metadata will be openly available.
      {%- endif %}
      {%- if metadataOpenFormAUuid == uuids.metadataOpenFormNoAUuid %}
        Metadata will not be available in a form that can be harvested and indexed.
      {%- elif metadataOpenFormAUuid == uuids.metadataOpenFormYesRepoAUuid %}
        Metadata will be available in a form that can be harvested and indexed (managed by the used repository / repositories).
      {%- elif metadataOpenFormAUuid == uuids.metadataOpenFormYesCareAUuid %}
        Metadata will be available in a form that can be harvested and indexed.
~~~

### Translation (zh_Hant)

~~~jinja

~~~
