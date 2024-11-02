from ib_insync import IB

# Initialize and connect IB instance
ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)