# HA_aliexpress_package_tracker_sensor
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)




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

# How to set Automation based on email
setup [IMAP integration](https://www.home-assistant.io/integrations/imap/) 
and create sensor for email content called "post_track". 
```
#configuration.yaml
template:
  - sensor:
    - name: post_track
      state: '{{ trigger.event.data["subject"] }}'
      attributes:
        body: "{{ trigger.event.data['text'] }}"
    trigger:
    - event_data:
        custom: '{{ "@postil.com" in sender  or "rate@chita-il.com" in sender }}'
      event_type: imap_content
      id: custom_event
      platform: event
```

create sensor for tracking number
```
#configuration.yaml
  sensor:
    new_tracking_namber_body:
          value_template: "{{ state_attr('sensor.post_track','body') | base64_decode | regex_findall_index('(([A-Z]){2}([0-9]){9,10}([A-Z]){0,2})')|first }}"
    new_tracking_namber_subject:
      value_template: "{{ state_attr('sensor.post_track','subject') | regex_findall_index('(([A-Z]){2}([0-9]){9,10}([A-Z]){0,2})')|first  }}"
```
```
#automation.yaml
- alias: track package when get email
  trigger:
  - platform: state
    entity_id:
    - sensor.new_tracking_namber_subject
    id: "subject"
  - platform: state
    entity_id:
    - sensor.new_tracking_namber_body
    id: "body"
  condition: []
  variables:
    src: sensor.new_tracking_namber_{{trigger.id}}
  action: 
  - service: aliexpress_package_tracker.add_tracking
    data:  
      tracking_number: "{{states(src)}}"
  mode: single   
```
