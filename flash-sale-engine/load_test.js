import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const EMAIL = __ENV.K6_EMAIL || 'moyzenjam096@gmail.com';
const PASSWORD = __ENV.K6_PASSWORD || 'abhi12345';
const FLASH_SALE_ID = Number(__ENV.FLASH_SALE_ID || 1);

export const options = {
  vus: Number(__ENV.K6_VUS || 20),
  duration: __ENV.K6_DURATION || '20s',
  thresholds: {
    http_req_failed: ['rate<0.15'],
    http_req_duration: ['p(95)<1200'],
  },
};

export function setup() {
  const res = http.post(
    `${BASE_URL}/auth/login`,
    JSON.stringify({ email: EMAIL, password: PASSWORD }),
    { headers: { 'Content-Type': 'application/json' } },
  );

  check(res, {
    'login ok': (r) => r.status === 200 && Boolean(r.json('access_token')),
  });

  return {
    token: res.json('access_token'),
  };
}

export default function (data) {
  const headers = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${data.token}`,
  };

  const joinRes = http.post(`${BASE_URL}/queue/${FLASH_SALE_ID}/join`, null, { headers });
  check(joinRes, {
    'queue join accepted': (r) => [200, 403, 404].includes(r.status),
  });

  let queueStatus = joinRes.json('status');
  for (let i = 0; queueStatus === 'queued' && i < 15; i += 1) {
    sleep(1);
    const positionRes = http.get(`${BASE_URL}/queue/${FLASH_SALE_ID}/position`, { headers });
    check(positionRes, {
      'queue position ok': (r) => r.status === 200,
    });
    queueStatus = positionRes.json('status');
  }

  if (queueStatus !== 'allowed') {
    return;
  }

  const orderPayload = JSON.stringify({
    flash_sale_id: FLASH_SALE_ID,
    quantity: 1,
    idempotency_key: `k6-${__VU}-${__ITER}-${Date.now()}`,
    berth_preference: 'Lower',
    passenger_names: `Load User ${__VU}`,
  });

  const orderRes = http.post(`${BASE_URL}/orders/`, orderPayload, { headers });
  check(orderRes, {
    'reserve ok or sold out': (r) => [200, 400, 429].includes(r.status),
  });

  if (orderRes.status !== 200) {
    return;
  }

  const orderId = orderRes.json('id');
  const payRes = http.post(
    `${BASE_URL}/orders/${orderId}/pay`,
    JSON.stringify({ simulate_failure: false }),
    { headers },
  );

  check(payRes, {
    'payment confirmed': (r) => r.status === 200 && r.json('status') === 'confirmed',
  });
}
