class Matrix:
    def __init__(self, matrix):
        self.matrix = matrix

    def __add__(self, other):
        assert len(other.matrix) == len(self.matrix) and len(other.matrix[0]) == len(self.matrix[0])

        new_matrix = [[] for _ in range(len(self.matrix))]

        for i in range(len(self.matrix)):
            for j in range(len(self.matrix[i])):
                new_matrix[i].append(self.matrix[i][j] + other.matrix[i][j])
        return Matrix(new_matrix)

    def _multiply_num(self, num):
        new_matrix = Matrix(self.matrix)
        for i in range(len(new_matrix.matrix)):
            for j in range(len(new_matrix.matrix[i])):
                new_matrix.matrix[i][j] *= num
        return new_matrix

    def transpose(self):
        self.matrix = list(zip(*self.matrix))

    def __rmul__(self, other):
        return self.__mul__(other)

    def __mul__(self, other):
        if type(other) is int:
            return self._multiply_num(other)
        elif type(other) is Matrix:
            zip_other = zip(*other.matrix)
            zip_other = list(zip_other)
            return Matrix([[sum(ele_a * ele_b for ele_a, ele_b in zip(row_a, col_b))
                            for col_b in zip_other] for row_a in self.matrix])

    def __str__(self):
        tmp_matrix_str = [" ".join(map(str, row)) for row in self.matrix]
        return "\n".join(tmp_matrix_str)

    def __repr__(self):
        return f"<Matrix {len(self.matrix)}x{len(self.matrix[0])}>"


if __name__ == '__main__':
    x = [[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12]]
    y = [[1, 2], [1, 2], [3, 4]]

    x_m = Matrix(x)
    y_m = Matrix(y)

    a = x_m * y_m
    a.transpose()
    print(a)
