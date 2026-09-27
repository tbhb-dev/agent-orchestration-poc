package relay

// PublishAck is the plain-value part of a broker publish result.
type PublishAck struct {
	Received  bool
	Stream    string
	Sequence  uint64
	Duplicate bool
}

// ClassifyPublish reports success only for a matching server acknowledgment.
func ClassifyPublish(expectedStream string, ack PublishAck) (string, uint64) {
	if !ack.Received || ack.Stream != expectedStream || ack.Sequence == 0 {
		return "unknown", 0
	}
	if ack.Duplicate {
		return "duplicate", ack.Sequence
	}
	return "stored", ack.Sequence
}

// ReceiveWait validates the requested wait and supplies the default in milliseconds.
func ReceiveWait(milliseconds int) (int, bool) {
	if milliseconds < 0 || milliseconds > 5000 {
		return 0, false
	}
	if milliseconds == 0 {
		return 1000, true
	}
	return milliseconds, true
}

// DeliveryFromMetadata accepts only metadata for the authenticated consumer.
func DeliveryFromMetadata(req Request, expectedStream, stream, consumer string, sequence, generation uint64) (Delivery, bool) {
	if stream != expectedStream || consumer != req.Agent || sequence == 0 || generation == 0 {
		return Delivery{}, false
	}
	return Delivery{Group: req.Group, Agent: req.Agent, Consumer: consumer, Sequence: sequence, Generation: generation}, true
}

// PlanInstall rejects stale deliveries and identifies older tokens to remove.
func PlanInstall(held map[string]Delivery, candidate Delivery) (bool, []string) {
	if candidate.Sequence == 0 || candidate.Generation == 0 {
		return false, nil
	}
	var remove []string
	for token, current := range held {
		if current.Group != candidate.Group || current.Consumer != candidate.Consumer || current.Sequence != candidate.Sequence {
			continue
		}
		if current.Generation >= candidate.Generation {
			return false, nil
		}
		remove = append(remove, token)
	}
	return true, remove
}

// CanConsume binds a live token to the authenticated request.
func CanConsume(owner Delivery, exists bool, req Request) bool {
	return exists && Owns(owner, req, req.Agent, owner.Sequence, owner.Generation)
}
