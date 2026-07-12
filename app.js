const road = document.querySelector("#road");
const vehicleLayer = document.querySelector("#vehicleLayer");

const startButton = document.querySelector("#startButton");
const pauseButton = document.querySelector("#pauseButton");
const resetButton = document.querySelector("#resetButton");

const speedSlider = document.querySelector("#speedSlider");
const speedValue = document.querySelector("#speedValue");

const statusIndicator = document.querySelector("#statusIndicator");
const statusText = document.querySelector("#statusText");

const createdCountElement = document.querySelector("#createdCount");
const crossingCountElement = document.querySelector("#crossingCount");

const eventList = document.querySelector("#eventList");
const emptyEventState = document.querySelector("#emptyEventState");

const BASE_VEHICLE_SPEED_PIXELS_PER_SECOND = 130;
const BASE_SPAWN_INTERVAL_MILLISECONDS = 1800;

const VEHICLE_WIDTH = 72;
const VEHICLE_HEIGHT = 112;
const SENSOR_Y_POSITION = 148;

const MAX_VISIBLE_EVENTS = 12;

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

  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function chooseRandomItem(items) {
  const randomIndex = Math.floor(Math.random() * items.length);
  return items[randomIndex];
}

function createVehicle() {
  const eventId = createEventId();
  const licensePlateId = chooseRandomItem(licensePlatePool);
  const color = chooseRandomItem(vehicleColors);

  const vehicleElement = document.createElement("div");
  vehicleElement.className = "vehicle";
  vehicleElement.style.setProperty("--vehicle-color", color);

  vehicleElement.innerHTML = `
    <div class="vehicle-window"></div>
    <div class="vehicle-roof-line"></div>
    <div class="license-plate">${licensePlateId}</div>
  `;

  const horizontalJitter = Math.random() * 12 - 6;
  const xPosition =
    (road.clientWidth - VEHICLE_WIDTH) / 2 + horizontalJitter;

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
  const elapsedSeconds = elapsedMilliseconds / 1000;

  const distance =
    BASE_VEHICLE_SPEED_PIXELS_PER_SECOND *
    simulationSpeed *
    elapsedSeconds;

  for (const vehicle of activeVehicles.values()) {
    vehicle.y -= distance;

    if (!vehicle.crossedSensor && vehicle.y <= SENSOR_Y_POSITION) {
      vehicle.crossedSensor = true;
      vehicle.element.classList.add("vehicle--crossed");

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
 * This function represents the physical toll sensor.
 *
 * Today:
 *   It records the crossing locally.
 *
 * Later:
 *   It will send this event to our FastAPI backend, which will
 *   publish the event into Kafka.
 */
function handleTollCrossing(vehicle) {
  const passageEvent = {
    eventId: vehicle.eventId,
    licensePlateId: vehicle.licensePlateId,
    timestamp: new Date().toISOString()
  };

  crossingCount += 1;
  crossingCountElement.textContent = crossingCount;

  addEventToLog(passageEvent);

  console.log("Toll passage detected:", passageEvent);

  /*
   * This will be added in the next backend stage:
   *
   * fetch("/api/toll-passages", {
   *   method: "POST",
   *   headers: {
   *     "Content-Type": "application/json"
   *   },
   *   body: JSON.stringify(passageEvent)
   * });
   */
}

function addEventToLog(passageEvent) {
  emptyEventState?.remove();

  const eventItem = document.createElement("li");
  eventItem.className = "event-item";

  const eventTime = new Date(
    passageEvent.timestamp
  ).toLocaleTimeString();

  eventItem.innerHTML = `
    <span class="event-number">${crossingCount}</span>

    <div class="event-details">
      <strong>${passageEvent.licensePlateId}</strong>
      <span>${passageEvent.eventId}</span>
    </div>

    <span class="event-time">${eventTime}</span>
  `;

  eventList.prepend(eventItem);

  while (eventList.children.length > MAX_VISIBLE_EVENTS) {
    eventList.lastElementChild.remove();
  }
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
      BASE_SPAWN_INTERVAL_MILLISECONDS / simulationSpeed;

    spawnAccumulatorMilliseconds += elapsedMilliseconds;

    while (spawnAccumulatorMilliseconds >= spawnInterval) {
      createVehicle();
      spawnAccumulatorMilliseconds -= spawnInterval;
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

  eventList.replaceChildren();

  const emptyState = document.createElement("li");
  emptyState.id = "emptyEventState";
  emptyState.className = "empty-event-state";
  emptyState.textContent =
    "Start the simulation to generate toll passage events.";

  eventList.appendChild(emptyState);

  startButton.disabled = false;
  pauseButton.disabled = true;

  setStatus("stopped");
}

function setStatus(status) {
  statusIndicator.className = "status-indicator";

  if (status === "running") {
    statusIndicator.classList.add("status-indicator--running");
    statusText.textContent = "Running";
    return;
  }

  if (status === "paused") {
    statusIndicator.classList.add("status-indicator--paused");
    statusText.textContent = "Paused";
    return;
  }

  statusIndicator.classList.add("status-indicator--stopped");
  statusText.textContent = "Stopped";
}

function updateSpeed() {
  simulationSpeed = Number(speedSlider.value);
  speedValue.textContent = `${simulationSpeed}×`;
}

startButton.addEventListener("click", startSimulation);
pauseButton.addEventListener("click", pauseSimulation);
resetButton.addEventListener("click", resetSimulation);
speedSlider.addEventListener("input", updateSpeed);

requestAnimationFrame(updateSimulation);