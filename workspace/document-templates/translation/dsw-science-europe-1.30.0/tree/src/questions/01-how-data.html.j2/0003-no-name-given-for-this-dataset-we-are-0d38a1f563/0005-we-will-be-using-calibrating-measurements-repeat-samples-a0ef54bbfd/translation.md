# Translation Unit

- Source File: `src/questions/01-how-data.html.j2`
- Wrapper Name: `__tr_block_0002`
- Wrapper Order: `3`
- Wrapper Key: `no-name-given-for-this-dataset-we-are-0d38a1f563`
- Unit Key: `we-will-be-using-calibrating-measurements-repeat-samples-a0ef54bbfd`
- Source Hash: `e5836c56fee02e93c1c5c85f9aca1804ae28c50f`
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
