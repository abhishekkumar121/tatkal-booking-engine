"use client";

import { useEffect, useRef, useState } from "react";
import { api, FlashSaleWithProduct, FlashSaleStatus, Order } from "@/lib/api";

type Step =
  | "login"
  | "signup"
  | "verify"
  | "select"
  | "prepare"
  | "board"
  | "payment"
  | "confirmed"
  | "failed";

type PaymentMethod = "upi" | "card" | "wallet" | null;

const AUTH_STORAGE_KEY = "tatkal-auth";
const AUTH_TTL_MS = 2 * 60 * 60 * 1000;

type StoredAuth = {
  token: string;
  email: string;
  expiresAt: number;
};

function saveStoredAuth(token: string, email: string) {
  localStorage.setItem(
    AUTH_STORAGE_KEY,
    JSON.stringify({
      token,
      email,
      expiresAt: Date.now() + AUTH_TTL_MS,
    } satisfies StoredAuth),
  );
}

function loadStoredAuth(): StoredAuth | null {
  const raw = localStorage.getItem(AUTH_STORAGE_KEY);
  if (!raw) return null;

  try {
    const auth = JSON.parse(raw) as StoredAuth;
    if (!auth.token || auth.expiresAt <= Date.now()) {
      localStorage.removeItem(AUTH_STORAGE_KEY);
      return null;
    }
    return auth;
  } catch {
    localStorage.removeItem(AUTH_STORAGE_KEY);
    return null;
  }
}

function clearStoredAuth() {
  localStorage.removeItem(AUTH_STORAGE_KEY);
}

function getErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Something went wrong";
}

export default function Home() {
  const [step, setStep] = useState<Step>("login");
  const [token, setToken] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState("");

  const [signupEmail, setSignupEmail] = useState("");
  const [signupPassword, setSignupPassword] = useState("");
  const [signupError, setSignupError] = useState("");
  const [signupMessage, setSignupMessage] = useState("");

  const [verifyCode, setVerifyCode] = useState("");
  const [verifyError, setVerifyError] = useState("");
  const [verifyMessage, setVerifyMessage] = useState("");

  const [availableSales, setAvailableSales] = useState<FlashSaleWithProduct[]>([]);
  const [selectedSale, setSelectedSale] = useState<FlashSaleWithProduct | null>(null);
  const [expandedTrains, setExpandedTrains] = useState<Record<string, boolean>>({});
  const [flashSaleId, setFlashSaleId] = useState("");
  const [saleStatus, setSaleStatus] = useState<FlashSaleStatus | null>(null);
  const [stock, setStock] = useState<number | null>(null);

  const [passengerCount, setPassengerCount] = useState(1);
  const [passengerNames, setPassengerNames] = useState<string[]>([""]);
  const [berthPreference, setBerthPreference] = useState("Lower");
  const [method, setMethod] = useState<PaymentMethod>(null);
  const [prepareError, setPrepareError] = useState("");

  const [queuePosition, setQueuePosition] = useState<number | null>(null);
  const [queueStatus, setQueueStatus] = useState<string>("");

  const [order, setOrder] = useState<Order | null>(null);
  const [payCountdown, setPayCountdown] = useState(60);
  const [upiId, setUpiId] = useState("");
  const [cardNumber, setCardNumber] = useState("");
  const [cvv, setCvv] = useState("");
  const [simulateFailure, setSimulateFailure] = useState(false);
  const [payError, setPayError] = useState("");

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const stockSocketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const storedAuth = loadStoredAuth();
    let cancelled = false;

    if (!storedAuth) return;

    Promise.resolve()
      .then(() => {
        if (cancelled) return;
        setToken(storedAuth.token);
        setEmail(storedAuth.email);
        setStep("select");
        return api.listFlashSalesDetailed();
      })
      .then((sales) => {
        if (!sales || cancelled) return;
        setAvailableSales(sales);
      })
      .catch(() => {
        if (cancelled) return;
        clearStoredAuth();
        setToken(null);
        setStep("login");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
      if (countdownRef.current) clearInterval(countdownRef.current);
      stockSocketRef.current?.close();
    };
  }, []);

  async function handleSignup() {
    setSignupError("");
    setSignupMessage("");
    try {
      await api.register(signupEmail, signupPassword);
      setSignupMessage("Verification code sent to your email.");
      setStep("verify");
    } catch (e: unknown) {
      setSignupError(getErrorMessage(e));
    }
  }

  async function handleVerify() {
    setVerifyError("");
    setVerifyMessage("");
    try {
      await api.verifyEmail(signupEmail, verifyCode);
      setVerifyMessage("Email verified! You can now log in.");
      setEmail(signupEmail);
      setTimeout(() => setStep("login"), 1500);
    } catch (e: unknown) {
      setVerifyError(getErrorMessage(e));
    }
  }

  async function handleLogin() {
    setLoginError("");
    try {
      const data = await api.login(email, password);
      setToken(data.access_token);
      saveStoredAuth(data.access_token, email);
      const sales = await api.listFlashSalesDetailed();
      setAvailableSales(sales);
      setStep("select");
    } catch (e: unknown) {
      setLoginError(getErrorMessage(e));
    }
  }

  function handleSavePrepare() {
    setPrepareError("");
    const filledPassengerNames = passengerNames
      .slice(0, passengerCount)
      .map((name) => name.trim());

    if (filledPassengerNames.some((name) => !name)) {
      setPrepareError("Add passenger name for every adult before saving your Tatkal profile.");
      return;
    }
    if (!method) {
      setPrepareError("Choose a payment type before entering the waiting room.");
      return;
    }
    setStep("board");
    startStockSocket();
  }

  function startStockSocket() {
    const id = parseInt(flashSaleId, 10);
    if (!id) return;

    stockSocketRef.current?.close();
    const socket = new WebSocket(api.stockSocketUrl(id));
    stockSocketRef.current = socket;

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data) as FlashSaleStatus & { total_stock?: number };
      setSaleStatus({
        id: data.id,
        status: data.status,
        product_id: data.product_id,
        start_time: data.start_time,
        end_time: data.end_time,
      });
      setStock(data.total_stock ?? null);
    };

    socket.onclose = () => {
      if (stockSocketRef.current === socket) {
        stockSocketRef.current = null;
      }
    };
  }

  async function handleBookNow() {
    if (!token) return;
    const id = parseInt(flashSaleId, 10);

    const q = await api.joinQueue(id, token);
    if (q.status === "queued") {
      setQueueStatus("queued");
      setQueuePosition(q.position ?? null);
      pollQueueUntilAllowed(id);
      return;
    }

    await reserveSeat(id);
  }

  function pollQueueUntilAllowed(id: number) {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      if (!token) return;
      const q = await api.checkPosition(id, token);
      if (q.status === "allowed") {
        if (pollRef.current) clearInterval(pollRef.current);
        setQueueStatus("allowed");
        await reserveSeat(id);
      } else {
        setQueuePosition(q.position ?? null);
      }
    }, 2000);
  }

  async function reserveSeat(id: number) {
    if (!token) return;
    try {
      const savedPassengerNames = passengerNames
        .slice(0, passengerCount)
        .map((name) => name.trim())
        .join(", ");
      const newOrder = await api.createOrder(
        id,
        passengerCount,
        token,
        berthPreference,
        savedPassengerNames
      );
      setOrder(newOrder);
      setStep("payment");
      startPaymentCountdown();
    } catch (e: unknown) {
      alert(getErrorMessage(e));
    }
  }

  function startPaymentCountdown() {
    setPayCountdown(60);
    if (countdownRef.current) clearInterval(countdownRef.current);
    countdownRef.current = setInterval(() => {
      setPayCountdown((prev) => {
        if (prev <= 1) {
          if (countdownRef.current) clearInterval(countdownRef.current);
          setPayError("Payment window expired — seat released. Please rejoin the queue.");
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  }

  async function handlePay() {
    if (!token || !order) return;
    setPayError("");
    try {
      const updated = await api.payOrder(order.id, simulateFailure, token);
      if (countdownRef.current) clearInterval(countdownRef.current);
      setOrder(updated);
      setUpiId("");
      setCardNumber("");
      setCvv("");
      setStep("confirmed");
    } catch (e: unknown) {
      if (countdownRef.current) clearInterval(countdownRef.current);
      setPayError(getErrorMessage(e));
      setUpiId("");
      setCardNumber("");
      setCvv("");
      setStep("failed");
    }
  }

  function formatCountdown(sec: number) {
    const m = String(Math.floor(sec / 60)).padStart(2, "0");
    const s = String(sec % 60).padStart(2, "0");
    return `${m}:${s}`;
  }

  function parseTrainProduct(productName: string) {
    const match = productName.match(/^(.*?)\s*(?:-|—|–)\s*(1A|2A|3A|SL|CC|EC|2S)$/i);
    if (!match) {
      return { trainName: productName.trim(), trainClass: productName.trim() };
    }

    return {
      trainName: match[1].trim(),
      trainClass: match[2].toUpperCase(),
    };
  }

  function getTrainClass(productName: string) {
    return parseTrainProduct(productName).trainClass;
  }

  function getTrainMeta(trainName: string) {
    if (trainName.toLowerCase().includes("rajdhani")) {
      return { number: "12951", route: ["NDLS", "MMCT"] };
    }
    if (trainName.toLowerCase().includes("duronto")) {
      return { number: "12259", route: ["SDAH", "NDLS"] };
    }
    return { number: "12002", route: ["SRC", "DEST"] };
  }

  function selectSaleForBooking(sale: FlashSaleWithProduct) {
    setSelectedSale(sale);
    setFlashSaleId(String(sale.id));
    setPassengerCount((current) => {
      const nextCount = Math.min(current, sale.max_per_user);
      setPassengerNames((names) => {
        const nextNames = names.slice(0, nextCount);
        while (nextNames.length < nextCount) nextNames.push("");
        return nextNames;
      });
      return nextCount;
    });
    setPrepareError("");
    setStep("prepare");
  }

  function updatePassengerCount(nextCount: number) {
    const maxPassengers = selectedSale?.max_per_user ?? 4;
    const clampedCount = Math.max(1, Math.min(nextCount, maxPassengers));
    setPassengerCount(clampedCount);
    setPassengerNames((names) => {
      const nextNames = names.slice(0, clampedCount);
      while (nextNames.length < clampedCount) nextNames.push("");
      return nextNames;
    });
  }

  function updatePassengerName(index: number, name: string) {
    setPassengerNames((names) => {
      const nextNames = [...names];
      nextNames[index] = name;
      return nextNames;
    });
  }

  const groupedSales = availableSales.reduce(
    (groups: Record<string, FlashSaleWithProduct[]>, sale) => {
      const { trainName } = parseTrainProduct(sale.product_name);
      if (!groups[trainName]) groups[trainName] = [];
      groups[trainName].push(sale);
      return groups;
    },
    {}
  );

  return (
    <>
      <div className="header">
        <div className="logo">
          Tatkal<span>Engine</span>
        </div>
      </div>

      <div className="wrap">
        {step === "login" && (
          <div className="card">
            <div className="card-title">Passenger Login</div>
            <label>Email</label>
            <input value={email} onChange={(e) => setEmail(e.target.value)} />
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <button className="btn-navy" onClick={handleLogin}>
              Log In
            </button>
            {loginError && <p className="status-err">{loginError}</p>}
            <p style={{ marginTop: 14, fontSize: 13, textAlign: "center" }}>
              New here?{" "}
              <span
                style={{ color: "var(--saffron-dark)", cursor: "pointer", fontWeight: 600 }}
                onClick={() => setStep("signup")}
              >
                Create an account
              </span>
            </p>
          </div>
        )}

        {step === "signup" && (
          <div className="card">
            <div className="card-title">Create Account</div>
            <label>Email</label>
            <input
              value={signupEmail}
              onChange={(e) => setSignupEmail(e.target.value)}
              placeholder="you@example.com"
            />
            <label>Password</label>
            <input
              type="password"
              value={signupPassword}
              onChange={(e) => setSignupPassword(e.target.value)}
              placeholder="At least 8 characters"
            />
            <button className="btn-navy" onClick={handleSignup}>
              Sign Up
            </button>
            {signupError && <p className="status-err">{signupError}</p>}
            {signupMessage && <p className="status-ok">{signupMessage}</p>}
            <p style={{ marginTop: 14, fontSize: 13, textAlign: "center" }}>
              Already have an account?{" "}
              <span
                style={{ color: "var(--saffron-dark)", cursor: "pointer", fontWeight: 600 }}
                onClick={() => setStep("login")}
              >
                Log in
              </span>
            </p>
          </div>
        )}

        {step === "verify" && (
          <div className="card">
            <div className="card-title">Verify Your Email</div>
            <p style={{ fontSize: 13, color: "var(--ink-muted)" }}>
              We sent a 6-digit code to <strong>{signupEmail}</strong>
            </p>
            <label>Verification Code</label>
            <input
              value={verifyCode}
              onChange={(e) => setVerifyCode(e.target.value)}
              placeholder="123456"
              maxLength={6}
            />
            <button className="btn-tatkal" onClick={handleVerify}>
              Verify
            </button>
            {verifyError && <p className="status-err">{verifyError}</p>}
            {verifyMessage && <p className="status-ok">{verifyMessage}</p>}
          </div>
        )}

        {step === "select" && (
          <div className="train-list">
            <div className="journey-strip">
              <div>
                <div className="card-title">Train List</div>
                <div className="journey-route">Tatkal Quota · E-Ticket</div>
              </div>
              <div className="quota-pill">TQ</div>
            </div>
            {availableSales.length === 0 && (
              <div className="empty-state">No Tatkal windows available right now.</div>
            )}
            {Object.entries(groupedSales).map(([trainName, classes]) => {
              const trainMeta = getTrainMeta(trainName);
              const isExpanded = expandedTrains[trainName] ?? false;

              return (
              <section key={trainName} className={`train-card ${isExpanded ? "expanded" : ""}`}>
                <button
                  className="train-head"
                  onClick={() =>
                    setExpandedTrains((current) => ({
                      ...current,
                      [trainName]: !isExpanded,
                    }))
                  }
                  aria-expanded={isExpanded}
                >
                  <div>
                    <div className="train-number">{trainMeta.number}</div>
                    <div className="train-name">{trainName}</div>
                  </div>
                  <div className="train-meta">
                    <span>{trainMeta.route[0]}</span>
                    <span>→</span>
                    <span>{trainMeta.route[1]}</span>
                    <span className="train-chevron">{isExpanded ? "▲" : "▼"}</span>
                  </div>
                </button>

                {isExpanded && (
                  <div className="availability-table">
                    <div className="availability-header">
                      <span>Class</span>
                      <span>Status</span>
                      <span>Availability</span>
                      <span>Fare</span>
                      <span>Action</span>
                    </div>

                    {classes.map((sale) => (
                      <div key={sale.id} className="availability-row">
                        <div className="class-cell">
                          <strong>{getTrainClass(sale.product_name)}</strong>
                          <span>Max {sale.max_per_user}/user</span>
                        </div>
                        <div>
                          <span className={`status-chip ${sale.status === "live" ? "live" : ""}`}>
                            {sale.status === "live" ? "LIVE" : "OPENS"}
                          </span>
                        </div>
                        <div className="seat-cell">
                          <strong>AVAILABLE {sale.total_stock}</strong>
                          <span>
                            {new Date(sale.start_time).toLocaleTimeString([], {
                              hour: "2-digit",
                              minute: "2-digit",
                            })}{" "}
                            to{" "}
                            {new Date(sale.end_time).toLocaleTimeString([], {
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </span>
                        </div>
                        <div className="fare-cell">₹{sale.price}</div>
                        <div>
                          <button
                            className="book-small"
                            onClick={() => selectSaleForBooking(sale)}
                          >
                            Book Now
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>
              );
            })}
          </div>
        )}

        {step === "prepare" && (
          <div className="profile-card">
            <div className="profile-top">
              <button className="back-link" onClick={() => setStep("select")}>
                ← Train list
              </button>
              <div className="profile-badge">Step 2 of 3</div>
            </div>

            <div className="profile-hero">
              <div>
                <div className="card-title">Save Tatkal Profile</div>
                <h2>{selectedSale?.product_name}</h2>
                <p>
                  Save passenger and payment choices now. When the Tatkal window is live,
                  only booking and payment remain.
                </p>
              </div>
              <div className={`status-chip ${selectedSale?.status === "live" ? "live" : ""}`}>
                {selectedSale?.status === "live" ? "LIVE" : "WAIT"}
              </div>
            </div>

            <div className="profile-grid">
              <div>
                <label>Adult passengers</label>
                <div className="adult-stepper">
                  <button
                    type="button"
                    onClick={() => updatePassengerCount(passengerCount - 1)}
                    disabled={passengerCount <= 1}
                    aria-label="Decrease adult count"
                  >
                    −
                  </button>
                  <strong>{passengerCount}</strong>
                  <button
                    type="button"
                    onClick={() => updatePassengerCount(passengerCount + 1)}
                    disabled={passengerCount >= (selectedSale?.max_per_user ?? 4)}
                    aria-label="Increase adult count"
                  >
                    +
                  </button>
                </div>
              </div>
              <div>
                <label>Berth Preference</label>
                <select value={berthPreference} onChange={(e) => setBerthPreference(e.target.value)}>
                  <option value="Lower">Lower</option>
                  <option value="Middle">Middle</option>
                  <option value="Upper">Upper</option>
                  <option value="Side Lower">Side Lower</option>
                  <option value="Side Upper">Side Upper</option>
                </select>
              </div>
            </div>

            <div className="passenger-name-list">
              {Array.from({ length: passengerCount }, (_, index) => (
                <div key={index}>
                  <label>Adult {index + 1} name</label>
                  <input
                    value={passengerNames[index] ?? ""}
                    onChange={(e) => updatePassengerName(index, e.target.value)}
                    placeholder={index === 0 ? "Example: Abhishek Kumar" : "Passenger full name"}
                  />
                </div>
              ))}
            </div>

            <label>Payment type</label>
            <div className="payment-choice-row">
              {(["upi", "card", "wallet"] as PaymentMethod[]).map((m) => (
                <button
                  key={m}
                  className={`payment-choice ${method === m ? "selected" : ""}`}
                  onClick={() => setMethod(m)}
                  type="button"
                >
                  <span>{m?.toUpperCase()}</span>
                  <small>{m === "upi" ? "Fastest" : m === "card" ? "Card pay" : "Wallet"}</small>
                </button>
              ))}
            </div>

            <div className="profile-summary">
              <div>
                <span>Fare</span>
                <strong>₹{selectedSale?.price}</strong>
              </div>
              <div>
                <span>Available</span>
                <strong>{selectedSale?.total_stock} seats</strong>
              </div>
              <div>
                <span>Max/User</span>
                <strong>{selectedSale?.max_per_user}</strong>
              </div>
            </div>

            {prepareError && <p className="status-err">{prepareError}</p>}

            <button className="btn-tatkal profile-action" onClick={handleSavePrepare}>
              Save Profile &amp; Enter Waiting Room
            </button>
          </div>
        )}

        {step === "board" && (
          <div className="waiting-room">
            <section className="waiting-status-card">
              <div className="waiting-top">
                <button className="back-link" onClick={() => setStep("prepare")}>
                  ← Edit profile
                </button>
                <div className="profile-badge">Profile Ready</div>
              </div>

              <div className="waiting-title-row">
                <div>
                  <div className="card-title">Tatkal Waiting Room</div>
                  <h2>{selectedSale?.product_name}</h2>
                </div>
                <span className={`window-state ${saleStatus?.status === "live" ? "live" : ""}`}>
                  {saleStatus?.status?.toUpperCase() ?? "CHECKING"}
                </span>
              </div>

              <div className="waiting-metrics">
                <div>
                  <span>Seats Available</span>
                  <strong>{stock ?? "—"}</strong>
                </div>
                <div>
                  <span>Fare</span>
                  <strong>₹{selectedSale?.price}</strong>
                </div>
                <div>
                  <span>Window</span>
                  <strong>
                    {selectedSale
                      ? new Date(selectedSale.start_time).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })
                      : "—"}
                  </strong>
                </div>
              </div>

              <div className="waiting-guidance">
                {saleStatus?.status === "live"
                  ? "Tatkal window is live. Your saved profile will be used for booking."
                  : "Profile saved. This screen refreshes availability automatically."}
              </div>
            </section>

            <div className="ready-card">
              <div className="summary-head">
                <div className="card-title">Saved Booking Details</div>
                <span>{method?.toUpperCase()} selected</span>
              </div>
              <div className="ready-grid">
                <div>
                  <span>Passenger(s)</span>
                  <strong>{passengerNames.slice(0, passengerCount).join(", ")}</strong>
                </div>
                <div>
                  <span>Berth</span>
                  <strong>{berthPreference}</strong>
                </div>
                <div>
                  <span>Payment</span>
                  <strong>{method?.toUpperCase()}</strong>
                </div>
                <div>
                  <span>Quantity</span>
                  <strong>{passengerCount}</strong>
                </div>
              </div>
              <button
                className="btn-tatkal"
                onClick={handleBookNow}
                disabled={saleStatus?.status !== "live" || (stock ?? 0) <= 0}
              >
                {saleStatus?.status === "live" ? "Book Tatkal Now" : "Waiting for Window"}
              </button>
              {queueStatus === "queued" && (
                <div className="queue-pill">
                  Queue position <strong>{queuePosition}</strong>
                </div>
              )}
            </div>
          </div>
        )}

        {step === "payment" && order && (
          <div className="card">
            <div className="card-title">
              Complete Payment — {selectedSale?.product_name}
            </div>
            <p>
              Seat held — Order #{order.id}. Pay within{" "}
              <strong>{formatCountdown(payCountdown)}</strong>
            </p>

            {method === "upi" && (
              <>
                <label>UPI ID</label>
                <input value={upiId} onChange={(e) => setUpiId(e.target.value)} placeholder="name@bank" />
              </>
            )}
            {method === "card" && (
              <>
                <label>Card Number</label>
                <input value={cardNumber} onChange={(e) => setCardNumber(e.target.value)} placeholder="•••• •••• •••• ••••" />
                <label>CVV</label>
                <input value={cvv} onChange={(e) => setCvv(e.target.value)} placeholder="•••" maxLength={3} />
              </>
            )}
            {method === "wallet" && <p>Pay via connected wallet.</p>}

            <label style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 10 }}>
              <input
                type="checkbox"
                style={{ width: "auto" }}
                checked={simulateFailure}
                onChange={(e) => setSimulateFailure(e.target.checked)}
              />
              Simulate gateway failure
            </label>

            <button className="btn-tatkal" onClick={handlePay} disabled={payCountdown === 0}>
              Pay &amp; Confirm
            </button>
            {payError && <p className="status-err">{payError}</p>}
          </div>
        )}

        {step === "confirmed" && order && (
          <div className="card" style={{ borderTop: "4px solid var(--green)" }}>
            <div className="card-title" style={{ color: "var(--green)" }}>
              ✓ Booking Confirmed
            </div>
            <div className="pnr-box active" style={{ marginBottom: 16 }}>
              <div className="pnr-label">PNR Number</div>
              <div className="pnr-code">PNR{String(order.id).padStart(9, "0")}</div>
            </div>
            <div style={{ fontSize: 14, lineHeight: 1.8 }}>
              <strong>Train:</strong> {selectedSale?.product_name}
              <br />
              <strong>Passenger(s):</strong> {order.passenger_names || "—"}
              <br />
              <strong>Berth Preference:</strong> {order.berth_preference || "—"}
              <br />
              <strong>Quantity:</strong> {order.quantity}
              <br />
              <strong>Status:</strong>{" "}
              <span className="status-ok">{order.status.toUpperCase()}</span>
            </div>
          </div>
        )}

        {step === "failed" && (
          <div className="card">
            <div className="card-title">Payment Failed</div>
            <p className="status-err">{payError}</p>
            <p>Seat released back to the pool. Refund initiated if applicable.</p>
            <button className="btn-navy" onClick={() => setStep("select")}>
              Back to Windows
            </button>
          </div>
        )}
      </div>
    </>
  );
}
