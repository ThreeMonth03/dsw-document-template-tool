# Translation Unit

- Source File: `src/questions/04-quality-control.html.j2`
- Wrapper Name: `__tr_block_0001`
- Wrapper Order: `2`
- Wrapper Key: `no-name-given-for-this-dataset-we-will-b159d2126e`
- Unit Key: `we-will-be-using-calibrating-measurements-repeat-samples-ae38efcc6e`
- Source Hash: `e94ac8db7041fd13596c1faa33fe75aa4735bd9f`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
We will be using calibrating measurements repeat samples/measurements standardized data capture/recording
```

### Source (en)

~~~jinja
We will be using
                        {% if calibrating -%}
                            calibrating measurements
                        {%- endif -%}
                        {%- if repetition -%}
                            repeat samples/measurements
                        {%- endif -%}
                        {%- if standardized -%}
                            standardized data capture/recording
                        {%- endif -%}
                        {%- if validation -%}
~~~

### Translation (zh_Hant)

~~~jinja

~~~
