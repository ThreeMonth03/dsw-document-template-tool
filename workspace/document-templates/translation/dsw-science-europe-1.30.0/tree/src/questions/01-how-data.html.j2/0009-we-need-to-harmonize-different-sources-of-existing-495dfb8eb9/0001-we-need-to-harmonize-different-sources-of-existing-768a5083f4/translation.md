# Translation Unit

- Source File: `src/questions/01-how-data.html.j2`
- Wrapper Name: `__tr_block_0008`
- Wrapper Order: `9`
- Wrapper Key: `we-need-to-harmonize-different-sources-of-existing-495dfb8eb9`
- Unit Key: `we-need-to-harmonize-different-sources-of-existing-768a5083f4`
- Source Hash: `61dcfcf7667cbe149bbcdf608dfdcac0d2d8dcc0`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
We need to harmonize different sources of existing data before reusing them {value}and we will make this harmonization results available to others / {value}but we won't make this harmonization results available to others.
```

### Source (en)

~~~jinja
We need to harmonize different sources of existing data before reusing them
      {%- set dataHarmonAvailable = [dataHarmo, uuids.dataHarmoYesAUuid, uuids.dataHarmoOthersQUuid]|reply_path  -%}
      {%- set dataHarmonAvailableReply = repliesMap[dataHarmonAvailable]|reply_str_value -%}
      {%- if dataHarmonAvailableReply == uuids.dataHarmoOthersYesAUuid -%}
        {{+" "}}and we will make this harmonization results available to others
      {%- elif dataHarmonAvailableReply == uuids.dataHarmoOthersNoAUuid -%}
        {{+" "}}but we won't make this harmonization results available to others
      {%- endif -%}
      .
~~~

### Translation (zh_Hant)

~~~jinja

~~~
