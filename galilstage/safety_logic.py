grb = stage.query_status("_GRB")
grb = float(grb.strip(': \r\n'))
print('grb before query ', grb)

posa = stage.query_status("_TPA")
posb = stage.query_status("_TPB")
print(posa, posb)

grb = stage.query_status("_GRB")
grb = float(grb.strip(': \r\n'))
print('grb after query', grb)

if grb == -1:
    stage.jog_axis(axis='A', speed=-15000)
    stage.begin_axis_motion('A')

move = True
while move:
    velA = stage.query_status("_TVA")
    torqueA = stage.query_status("_TTA")
    torqueB = stage.query_status("_TTB")
    velB = stage.query_status("_TVB")
    velA = float(velA.strip(': \r\n'))
    velB = float(velB.strip(': \r\n'))
    grb = stage.query_status("_GRB")
    grb = float(grb.strip(': \r\n'))
    print('velA', velA, 'velB', velB, 'TTA', torqueA, 'TTB', torqueB, 'GRA', 'GRB', stage.query_status("_GRB"))

    
    if np.abs(velA - velB) >= 1000 or grb != -1.0:
        stage.stop('A')
        #stage.stop('B')
        print('grb', grb)
        move = False
    
#print("checking stage state", , print(type(stage.query_status("_TVA")))
#print("checking stage state", stage.query_status("_TVB"))
