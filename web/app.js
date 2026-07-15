const road = document.querySelector("#road");
const vehicleLayer = document.querySelector("#vehicleLayer");

const startButton = document.querySelector("#startButton");
const pauseButton = document.querySelector("#pauseButton");
const resetButton = document.querySelector("#resetButton");

const speedSlider = document.querySelector("#speedSlider");
const speedValue = document.querySelector("#speedValue");

const statusIndicator = document.querySelector("#statusIndicator");
const statusText = document.querySelector("#statusText");

const createdCountElement =
  document.querySelector("#createdCount");

const crossingCountElement =
  document.querySelector("#crossingCount");

const eventList = document.querySelector("#eventList");

const API_BASE_URL = "http://127.0.0.1:8001";
const DEBT_REFRESH_INTERVAL_MILLISECONDS = 1000;

const BASE_VEHICLE_SPEED_PIXELS_PER_SECOND = 130;
const BASE_SPAWN_INTERVAL_MILLISECONDS = 1800;

const VEHICLE_WIDTH = 72;
const VEHICLE_HEIGHT = 112;
const SENSOR_Y_POSITION = 148;

const licensePlatePool = [
  "ABC-123",
  "NYC-742",
  "EV-2026",
  "XYZ-908",
  "CAR-007",
  "TOLL-15",
  "MTA-419",
  "ABC-123"
];

const vehicleColors = [
  "#5f8ee4",
  "#da6161",
  "#4ea979",
  "#e7aa45",
  "#9b78d0",
  "#d9dce2"
];

const currencyFormatter = new Intl.NumberFormat(
  "en-US",
  {
    style: "currency",
    currency: "USD"
  }
);

let isRunning = false;
let simulationSpeed = Number(speedSlider.value);

let previousFrameTime = null;
let spawnAccumulatorMilliseconds = 0;

let createdCount = 0;
let crossingCount = 0;

const activeVehicles = new Map();

function createEventId() {
  if (
    typeof crypto !== "undefined" &&
    typeof crypto.randomUUID === "function"
  ) {
    return crypto.randomUUID();
  }

  return `${Date.now()}-${Math.random()
    .toString(16)
    .slice(2)}`;
}

function chooseRandomItem(items) {
  const randomIndex = Math.floor(
    Math.random() * items.length
  );

  return items[randomIndex];
}

function createVehicle() {
  const eventId = createEventId();
  const licensePlateId = chooseRandomItem(
    licensePlatePool
  );
  const color = chooseRandomItem(vehicleColors);

  const vehicleElement = document.createElement("div");

  vehicleElement.className = "vehicle";
  vehicleElement.style.setProperty(
    "--vehicle-color",
    color
  );

  vehicleElement.innerHTML = `
    <div class="vehicle-window"></div>
    <div class="vehicle-roof-line"></div>
    <div class="license-plate">${licensePlateId}</div>
  `;

  const horizontalJitter = Math.random() * 12 - 6;

  const xPosition =
    (road.clientWidth - VEHICLE_WIDTH) / 2 +
    horizontalJitter;

  const yPosition = road.clientHeight + 20;

  const vehicle = {
    eventId,
    licensePlateId,
    x: xPosition,
    y: yPosition,
    crossedSensor: false,
    element: vehicleElement
  };

  updateVehiclePosition(vehicle);

  vehicleLayer.appendChild(vehicleElement);
  activeVehicles.set(eventId, vehicle);

  createdCount += 1;
  createdCountElement.textContent = createdCount;
}

function updateVehiclePosition(vehicle) {
  vehicle.element.style.transform =
    `translate3d(${vehicle.x}px, ${vehicle.y}px, 0)`;
}

function updateVehicles(elapsedMilliseconds) {
  const elapsedSeconds =
    elapsedMilliseconds / 1000;

  const distance =
    BASE_VEHICLE_SPEED_PIXELS_PER_SECOND *
    simulationSpeed *
    elapsedSeconds;

  for (const vehicle of activeVehicles.values()) {
    vehicle.y -= distance;

    if (
      !vehicle.crossedSensor &&
      vehicle.y <= SENSOR_Y_POSITION
    ) {
      vehicle.crossedSensor = true;

      vehicle.element.classList.add(
        "vehicle--crossed"
      );

      handleTollCrossing(vehicle);
    }

    updateVehiclePosition(vehicle);

    if (vehicle.y < -VEHICLE_HEIGHT - 30) {
      removeVehicle(vehicle);
    }
  }
}

function removeVehicle(vehicle) {
  vehicle.element.remove();
  activeVehicles.delete(vehicle.eventId);
}

/**
 * Represents the toll sensor detecting a vehicle.
 *
 * The frontend sends the passage to FastAPI.
 * FastAPI publishes it to Kafka.
 * The consumer later stores it in MySQL.
 */
async function handleTollCrossing(vehicle) {
  const passageEvent = {
    eventId: vehicle.eventId,
    licensePlateId: vehicle.licensePlateId,
    timestamp: new Date().toISOString()
  };

  crossingCount += 1;
  crossingCountElement.textContent = crossingCount;

  console.log(
    "Toll passage detected:",
    passageEvent
  );

  try {
    const response = await fetch(
      `${API_BASE_URL}/toll-passages`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(passageEvent)
      }
    );

    if (!response.ok) {
      throw new Error(
        `API returned status ${response.status}`
      );
    }

    console.log(
      "Toll passage accepted by API:",
      passageEvent.eventId
    );
  } catch (error) {
    console.error(
      "Failed to send toll passage:",
      error
    );
  }
}

function formatDebt(totalDebtCents) {
  return currencyFormatter.format(
    totalDebtCents / 100
  );
}

async function fetchDebts() {
  try {
    const response = await fetch(
      `${API_BASE_URL}/debts`
    );

    if (!response.ok) {
      throw new Error(
        `Debt API returned status ${response.status}`
      );
    }

    const debts = await response.json();

    renderDebts(debts);
  } catch (error) {
    console.error(
      "Failed to fetch debts:",
      error
    );
  }
}

function renderDebts(debts) {
  eventList.replaceChildren();

  if (debts.length === 0) {
    const emptyState = document.createElement("li");

    emptyState.className = "empty-event-state";
    emptyState.textContent =
      "No toll debts have been recorded yet.";

    eventList.appendChild(emptyState);
    return;
  }

  debts.forEach((debt, index) => {
    const debtItem = document.createElement("li");
    debtItem.className = "event-item";

    const position = document.createElement("span");
    position.className = "event-number";
    position.textContent = String(index + 1);

    const details = document.createElement("div");
    details.className = "event-details";

    const licensePlate =
      document.createElement("strong");

    licensePlate.textContent =
      debt.licensePlateId;

    const description =
      document.createElement("span");

    description.textContent =
      "Outstanding toll debt";

    details.appendChild(licensePlate);
    details.appendChild(description);

    const amount = document.createElement("span");
    amount.className = "event-time";

    amount.textContent = formatDebt(
      debt.totalDebtCents
    );

    debtItem.appendChild(position);
    debtItem.appendChild(details);
    debtItem.appendChild(amount);

    eventList.appendChild(debtItem);
  });
}

async function continuouslyRefreshDebts() {
  await fetchDebts();

  setTimeout(
    continuouslyRefreshDebts,
    DEBT_REFRESH_INTERVAL_MILLISECONDS
  );
}

function updateSimulation(timestamp) {
  if (previousFrameTime === null) {
    previousFrameTime = timestamp;
  }

  const elapsedMilliseconds = Math.min(
    timestamp - previousFrameTime,
    100
  );

  previousFrameTime = timestamp;

  if (isRunning) {
    const spawnInterval =
      BASE_SPAWN_INTERVAL_MILLISECONDS /
      simulationSpeed;

    spawnAccumulatorMilliseconds +=
      elapsedMilliseconds;

    while (
      spawnAccumulatorMilliseconds >=
      spawnInterval
    ) {
      createVehicle();

      spawnAccumulatorMilliseconds -=
        spawnInterval;
    }

    updateVehicles(elapsedMilliseconds);
  }

  requestAnimationFrame(updateSimulation);
}

function startSimulation() {
  if (isRunning) {
    return;
  }

  isRunning = true;

  if (activeVehicles.size === 0) {
    createVehicle();
    spawnAccumulatorMilliseconds = 0;
  }

  startButton.disabled = true;
  pauseButton.disabled = false;

  setStatus("running");
}

function pauseSimulation() {
  isRunning = false;

  startButton.disabled = false;
  pauseButton.disabled = true;

  setStatus("paused");
}

function resetSimulation() {
  isRunning = false;

  for (const vehicle of activeVehicles.values()) {
    vehicle.element.remove();
  }

  activeVehicles.clear();

  createdCount = 0;
  crossingCount = 0;
  spawnAccumulatorMilliseconds = 0;

  createdCountElement.textContent = "0";
  crossingCountElement.textContent = "0";

  startButton.disabled = false;
  pauseButton.disabled = true;

  setStatus("stopped");
}

function setStatus(status) {
  statusIndicator.className =
    "status-indicator";

  if (status === "running") {
    statusIndicator.classList.add(
      "status-indicator--running"
    );

    statusText.textContent = "Running";
    return;
  }

  if (status === "paused") {
    statusIndicator.classList.add(
      "status-indicator--paused"
    );

    statusText.textContent = "Paused";
    return;
  }

  statusIndicator.classList.add(
    "status-indicator--stopped"
  );

  statusText.textContent = "Stopped";
}

function updateSpeed() {
  simulationSpeed = Number(
    speedSlider.value
  );

  speedValue.textContent =
    `${simulationSpeed}×`;
}

startButton.addEventListener(
  "click",
  startSimulation
);

pauseButton.addEventListener(
  "click",
  pauseSimulation
);

resetButton.addEventListener(
  "click",
  resetSimulation
);

speedSlider.addEventListener(
  "input",
  updateSpeed
);

requestAnimationFrame(updateSimulation);
continuouslyRefreshDebts();