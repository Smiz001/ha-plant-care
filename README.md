# Plant Care Scheduler (Home Assistant)

Add the integration once, then add each plant inside it. Each plant becomes its own device with
a watering/feeding schedule, days-left sensors, "needs water/feed" binary sensors, "watered/fed"
buttons, an aggregate calendar, and optional reminders via any notify service. Attach a soil-moisture
sensor to a plant later via Reconfigure.

## Install (HACS custom repository)
HACS → ⋮ → Custom repositories → add `https://github.com/Smiz001/ha-plant-care`, category **Integration** → install → restart Home Assistant.

## Use
1. Settings → Devices & Services → **Add Integration** → **Plant Care Scheduler** (creates the hub, once).
2. On the Plant Care Scheduler hub card, **Add plant** — fill name, emoji, watering/feeding intervals, next dates, and optionally a moisture sensor.
3. Edit a plant's intervals/next-dates on its entities; use **Reconfigure** on a plant to attach or change a moisture sensor.
4. (Optional) Configure the hub: a reminder time + a notify service (e.g. `notify.telegram`) to get daily reminders.

## Entities (per plant)
- `number`: water interval, feed interval
- `date`: next watering, next feeding
- `sensor`: days to watering, days to feeding
- `binary_sensor`: needs watering, needs feeding (uses the moisture sensor when attached, else the calendar)
- `button`: mark watered, mark fed
- one aggregate `calendar.plant_care_scheduler` across all plants

## Telegram interactive reminder (optional automation example)
The integration is notifier-agnostic. For a tappable Telegram button that marks a plant watered:
```yaml
triggers:
  - trigger: state
    entity_id: binary_sensor.<your_plant>_needs_watering
    to: "on"
actions:
  - action: telegram_bot.send_message
    data:
      message: "🌼 Time to water <your plant>"
      inline_keyboard:
        - "✅ Watered:/pc_water_<your_plant>"
# Then a telegram_callback automation presses button.<your_plant>_mark_watered.
```

## Development
```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements_test.txt
python -m pytest -q
```
