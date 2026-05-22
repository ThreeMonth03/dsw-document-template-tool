# Translation Unit

- Source File: `src/questions/01-how-data.html.j2`
- Wrapper Name: `__tr_block_0009`
- Wrapper Order: `10`
- Wrapper Key: `we-will-need-to-re-made-the-data-95471ddecb`
- Unit Key: `we-will-need-to-re-made-the-data-c60abc547c`
- Source Hash: `16554c67b1dbf34a94d4ead0bba5102c85491f2d`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
We will need to (re-)made the data into computer readable form before their using {value}and we will make this computer readable form available to others through a standard repository / {value}and we will make this computer readable form available to others / {value}but we won't make this computer readable form available to others. We will provide machine readable, standardized metadata to others {value}and we will use following Metadata Standards: {value} {value}{value} /.
```

### Source (en)

~~~jinja
We will need to (re-)made the data into computer readable form before their using

      {%- set dataCompReadItself = [dataCompRead, uuids.dataCompReadYesAUuid, uuids.dataCompReadItselfQUuid]|reply_path -%}
      {%- set dataCompReadItselfReply = repliesMap[dataCompReadItself]|reply_str_value -%}
      {%- set dataCompReadOthers = [dataCompRead, uuids.dataCompReadYesAUuid, uuids.dataCompReadOthersQUuid]|reply_path  -%}
      {%- set dataCompReadOthersReply = repliesMap[dataCompReadOthers]|reply_str_value -%}

      {%- if dataCompReadItselfReply -%}
        {%- if dataCompReadItselfReply == uuids.dataCompReadItselfYesAUuid -%}
          {{+" "}}and we will make this computer readable form available to others through a standard repository
        {%- elif dataCompReadItselfReply == uuids.dataCompReadItselfYesOtherAUuid -%} 
          {{+" "}}and we will make this computer readable form available to others
        {%- elif dataCompReadItselfReply == uuids.dataCompReadItselfNoAUuid -%}
          {{+" "}}but we won't make this computer readable form available to others
        {%- endif -%}
      {%- endif -%}
      .

      {%- if dataCompReadOthersReply -%}
        {%- if dataCompReadOthersReply == uuids.dataCompReadOthersYesAUuid %}
            We will provide machine readable, standardized metadata to others
            {%- set dataCompReadWhichMetadataStandardPath = [dataCompReadOthers, uuids.dataCompReadOthersYesAUuid, uuids.dataCompReadOthersYesStandardsQUuid]|reply_path -%}
            {%- set dataCompReadMetadataStandardItems =  repliesMap[dataCompReadWhichMetadataStandardPath]|reply_items -%}
            {%- if dataCompReadMetadataStandardItems|length  > 0 -%}
              {{+" "}}and we will use following Metadata Standards:{{+" "}}
                {%- for dataCompReadMetadataStandardItem in dataCompReadMetadataStandardItems -%}
                  {%- set dataCompReadMetadataStandardPrefix = [dataCompReadWhichMetadataStandardPath, dataCompReadMetadataStandardItem]|reply_path -%}
                  {%- set dataCompReadMetadataStandard = [dataCompReadMetadataStandardPrefix, uuids.dataCompReadOthersYesStandardQUuid]|reply_path -%}
                  {%- set dataCompReadMetadataStandardReply = repliesMap[dataCompReadMetadataStandard] -%}
                  {{ macros.integrationFairSharing(dataCompReadMetadataStandardReply) }}{{ ", " if not loop.last else "." }}
                {%- endfor -%}
            {%- else -%}
            .
            {%- endif -%}

        {%- endif -%}
~~~

### Translation (zh_Hant)

~~~jinja

~~~
