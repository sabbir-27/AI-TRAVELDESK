# AI TravelDesk — Website Integration Guide

AI TravelDesk supports three integration channels for independent travel agencies.

## 1. Embeddable JavaScript Chatbot Widget

1. Navigate to **Agency Portal → Integrations** (`/agency/integrations`) as `AGENCY_OWNER`.
2. Add your authorized website origins (e.g. `https://www.youragency.com`).
3. Click **Generate / Rotate Widget Token** to issue an origin-scoped public widget token (`atd_wgt_...`).
4. Embed the generated `<script>` snippet before `</body>` on your website:

```html
<script
  src="https://api.yourplatform.com/widget.js"
  data-agency-id="YOUR_AGENCY_UUID"
  data-widget-token="atd_wgt_PUBLIC_SCOPED_TOKEN"
></script>
```

### Security Guarantees
- The widget **never** embeds private REST API keys (`atd_live_...`) or JWTs.
- Public widget endpoints (`/api/v1/widget/*`) validate `X-Widget-Token`, verify `X-Agency-ID` matches the credential's tenant, verify `Agency.status == ACTIVE`, and enforce `Origin` against your agency's `allowed_origins`.
- White-label branding (`primary_color`, `secondary_color`, `brand_name`, `agent_name`, `welcome_message`) is fetched dynamically from `/api/v1/widget/config`.

## 2. Versioned Server-to-Server REST API

1. Issue a server API key (`atd_live_...`) in **Agency Portal → Integrations** (`POST /api/v1/agency/integrations/api-keys`).
2. Store the secret key securely in your backend environment (never in browser JavaScript).
3. Pass `X-API-Key: atd_live_...` on API requests:
   - `POST /api/v1/flights/search`
   - `POST /api/v1/flights/price`
   - `POST /api/v1/bookings`
   - `POST /api/v1/agent/conversations`
   - `POST /api/v1/agent/conversations/{id}/messages`

## 3. White-Label Portal

Customize your brand colors, display name, service fees (`/agency/branding`), and AI consultant persona (`/agency/agents`) so customers interact exclusively with your agency identity.
