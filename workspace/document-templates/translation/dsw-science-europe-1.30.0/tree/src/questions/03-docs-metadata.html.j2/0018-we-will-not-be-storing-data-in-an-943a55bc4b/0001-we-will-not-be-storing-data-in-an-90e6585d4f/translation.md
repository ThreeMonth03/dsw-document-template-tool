# Translation Unit

- Source File: `src/questions/03-docs-metadata.html.j2`
- Wrapper Name: `__tr_block_0017`
- Wrapper Order: `18`
- Wrapper Key: `we-will-not-be-storing-data-in-an-943a55bc4b`
- Unit Key: `we-will-not-be-storing-data-in-an-90e6585d4f`
- Source Hash: `2c8fabc12e0b5973344e760845c4743cc8f9f29e`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
We will not be storing data in an "object/document store" system. / We will be storing data in an "object/document store" system using following naming conventions for objects in the store: {scObjStoreNaming} / We will be storing data in an "object/document store" system.
```

### Source (en)

~~~jinja
{%- if storageConvObjStoreAUuid == uuids.storageConvObjStoreNoAUuid -%}
        We will not be storing data in an "object/document store" system.
      {%- elif storageConvObjStoreAUuid == uuids.storageConvObjStoreYesAUuid -%}
        {%- set scObjStoreNamingQUuid = [storageConvObjStorePath, uuids.storageConvObjStoreYesAUuid, uuids.scObjStoreNamingQUuid]|reply_path -%}
        {%- set scObjStoreNaming = repliesMap[scObjStoreNamingQUuid]|reply_str_value -%}
        {%- if scObjStoreNaming -%} 
          We will be storing data in an "object/document store" system using following naming conventions for objects in the store: {{ scObjStoreNaming|dot }}
        {%- else -%}
          We will be storing data in an "object/document store" system.
        {%- endif -%}
~~~

### Translation (zh_Hant)

~~~jinja

~~~
