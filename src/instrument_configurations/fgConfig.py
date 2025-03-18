import json

class fgConfig: 
    def __init__(self, name, frequency, amplitude, offset):
        self.name = name
        self.frequency = frequency
        self.amplitude = amplitude
        self.offset = offset
    
    def to_dict(self):
        return {
            'name': self.name,
            'frequency': self.frequency,
            'amplitude': self.amplitude,
            'offset': self.offset
        }
  
    def to_json(self, filepath):
        with open(filepath, 'w') as file:
            json.dump(self.to_dict(), file, indent=4)


# ##################### DEBUG #####################
# if __name__ == "__main__":
#     config = fgConfig('example', 1000, 5.0, 0.0)
#     config.to_json('example.json')