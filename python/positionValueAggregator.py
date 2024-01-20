import pdb


with open("positionValues.txt") as f:
    values = []
    position = 0
    while line := f.readline().strip():
        values.append((position, float(line)))
        position += 1
    values = sorted(values, key=lambda x: x[1], reverse=True)
    pdb.set_trace()