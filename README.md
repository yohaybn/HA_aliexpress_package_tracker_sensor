# HA_aliexpress_package_tracker_sensor
```
#configuration.yaml
  sensor:
  - platform: aliexpress_package_tracker
    lang: he-IL #optional
 ```
```
#markdown card
type: markdown
content: >-
  {% for entity in (states.sensor | selectattr('name', 'search',
  'Aliexpress_package_no_*')|rejectattr('state','eq','unavailable')) %}
    >- {% if "carrier_url" in entity.attributes-%}[<ha-icon icon="mdi:information-outline"></ha-icon>]({{entity.attributes.carrier_url}}){%endif %} **{{ entity.attributes.title }} ({{
  entity.attributes.order_number }}{% if "realMailNo" in entity.attributes-%}
    / {{entity.attributes.realMailNo }}
  {%- endif %}):**
  
  {% if "last_update_status" in entity.attributes-%}
    {{entity.attributes.last_update_status }}
  {%- endif %}
  
  {% if "daysNumber" in entity.attributes-%}  
  בדרך כבר: {{entity.attributes.daysNumber   }}  
  {%- endif %}

  {% if "estimated_max_delivery_date" in entity.attributes-%}  
  יגיע עד: {{entity.attributes.estimated_max_delivery_date | timestamp_custom(' %-d /  %-m ')  }}  
  {%- endif %}
  
  {% endfor %}

 ```
