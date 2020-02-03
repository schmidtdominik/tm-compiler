from compiler import Var, Program, If, While

a = Var('a')
b = Var('b')
c = Var('c')
x = Var('x')
y = Var('y')
z = Var('z')

mult = Program([
    z <= 0,
    While(x > 0, Program([
        z <= z+y,
        x <= x-1
    ]))
])

print(mult)
print('-'*30)
print(mult.as_atomized)
print('-'*30)
print(mult.execute({x: 5, y: 3}))
print(mult.as_atomized.execute({x: 5, y: 3}))
print('\n'*3)


fac = Program([
    y <= 1,
    While(x > 0, Program([
        y <= y*x,
        x <= x-1
    ]))
])

print(fac)
print('-'*30)
print(fac.as_atomized)
print('-'*30)
print(fac.execute({x: 15}))
print(fac.as_atomized.execute({x: 15}))
print('\n'*3)


prime_checker = Program([
    z <= 1,
    c <= 2,
    While(c < x, Program([
        b <= x // c,
        If((b*c) == x, Program([
            z <= 0
        ]), Program([])),

        c <= c+1
    ]))
])

print(prime_checker)
print('-'*30)
print(prime_checker.as_atomized)
print('-'*30)
print(prime_checker.execute({x: 3}))
print(prime_checker.as_atomized.execute({x: 3}))
print('\n'*3)
