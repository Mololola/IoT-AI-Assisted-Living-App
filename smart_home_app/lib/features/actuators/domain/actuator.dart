// FILE: lib/features/actuators/domain/actuator.dart
// Domain model for actuators and the alert-to-actuator mapping.
// This defines what actuators exist, their MQTT topics, and which
// ones should be suggested for each alert type.

class Actuator {
  final String id;
  final String name;
  final String room;
  final String mqttTopic;
  final String iconName;
  final List<ActuatorCommand> commands;

  const Actuator({
    required this.id,
    required this.name,
    required this.room,
    required this.mqttTopic,
    required this.iconName,
    required this.commands,
  });
}

class ActuatorCommand {
  final String label; // "Turn On", "Open", "Lock"
  final String payload; // "ON", "OPEN", "LOCK"
  final String? undoLabel; // "Turn Off", "Close", "Unlock"
  final String? undoPayload; // "OFF", "CLOSE", "UNLOCK"

  const ActuatorCommand({
    required this.label,
    required this.payload,
    this.undoLabel,
    this.undoPayload,
  });
}

/// All actuators in the system (from config.json)
class ActuatorRegistry {
  static const hallwayLeds = Actuator(
    id: 'hallway_leds',
    name: 'Hallway Lights',
    room: 'Hallway',
    mqttTopic: 'home/hallway/led',
    iconName: 'lightbulb',
    commands: [
      ActuatorCommand(
        label: 'Turn On',
        payload: 'ON',
        undoLabel: 'Turn Off',
        undoPayload: 'OFF',
      ),
    ],
  );

  static const frontDoorLock = Actuator(
    id: 'frontdoor_lock',
    name: 'Front Door Lock',
    room: 'Hallway',
    mqttTopic: 'home/frontdoor/lock',
    iconName: 'lock',
    commands: [
      ActuatorCommand(
        label: 'Unlock',
        payload: 'UNLOCK',
        undoLabel: 'Lock',
        undoPayload: 'LOCK',
      ),
    ],
  );

  static const bedroomBlinds = Actuator(
    id: 'bedroom_blinds',
    name: 'Bedroom Blinds',
    room: 'Bedroom',
    mqttTopic: 'home/bedroom/blinds',
    iconName: 'blinds',
    commands: [
      ActuatorCommand(
        label: 'Open',
        payload: 'OPEN',
        undoLabel: 'Close',
        undoPayload: 'CLOSE',
      ),
    ],
  );

  static const livingRoomBlinds = Actuator(
    id: 'livingroom_blinds',
    name: 'Living Room Blinds',
    room: 'Living Room',
    mqttTopic: 'home/livingroom/blinds',
    iconName: 'blinds',
    commands: [
      ActuatorCommand(
        label: 'Open',
        payload: 'OPEN',
        undoLabel: 'Close',
        undoPayload: 'CLOSE',
      ),
    ],
  );

  static const all = [
    hallwayLeds,
    frontDoorLock,
    bedroomBlinds,
    livingRoomBlinds,
  ];

  /// Given an alert rule_type, return the relevant actuators and their
  /// suggested actions. This is the alert → actuator mapping.
  static List<ActuatorAction> actionsForAlert(String ruleType) {
    final type = ruleType.toLowerCase();

    if (type.contains('fall') || type.contains('possible_fall')) {
      return [
        ActuatorAction(actuator: hallwayLeds, commandIndex: 0),
        ActuatorAction(actuator: bedroomBlinds, commandIndex: 0),
        ActuatorAction(
          actuator: frontDoorLock,
          commandIndex: 0,
        ), // Unlock for emergency
      ];
    }

    if (type.contains('night_wandering') || type.contains('wander')) {
      return [ActuatorAction(actuator: hallwayLeds, commandIndex: 0)];
    }

    if (type.contains('bed_empty') || type.contains('out_of_bed')) {
      return [ActuatorAction(actuator: hallwayLeds, commandIndex: 0)];
    }

    if (type.contains('bathroom_too_long') || type.contains('bathroom')) {
      return [ActuatorAction(actuator: hallwayLeds, commandIndex: 0)];
    }

    if (type.contains('no_activity') ||
        type.contains('inactivity') ||
        type.contains('prolonged_inactivity')) {
      return [
        ActuatorAction(actuator: bedroomBlinds, commandIndex: 0),
        ActuatorAction(actuator: livingRoomBlinds, commandIndex: 0),
        ActuatorAction(actuator: hallwayLeds, commandIndex: 0),
        ActuatorAction(
          actuator: frontDoorLock,
          commandIndex: 0,
        ), // Unlock for emergency
      ];
    }

    if (type.contains('ml_')) {
      return [ActuatorAction(actuator: hallwayLeds, commandIndex: 0)];
    }

    // Default: hallway lights for any unknown alert type
    if (type.contains('high') || type.contains('medium')) {
      return [ActuatorAction(actuator: hallwayLeds, commandIndex: 0)];
    }

    return []; // INFO/summary alerts — no actuator action
  }
}

/// A specific action to take: which actuator + which command
class ActuatorAction {
  final Actuator actuator;
  final int commandIndex;

  const ActuatorAction({required this.actuator, required this.commandIndex});

  ActuatorCommand get command => actuator.commands[commandIndex];
}
