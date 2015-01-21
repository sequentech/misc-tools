agora-admin.py
==============

Scritp para crear auth-event, añadir un censo y comenzar o parar el auth-event

Uso:

Cambiar en el script el usuario administrador que tengamos en authapi y las url de las apis.

Necesitamos 3 ficheros de configuración: id.json, id.config.json e id.census.json, dentro de la
carpeta /gforms tenemos 2 ejemplos. Para generar el auth-event y añadir el censo, hacemos lo
siguiente:

    ./agora-admin.py --create gforms/<id>

El comando nos mostrará en la salida el id del auth-event creado, el cual usaremos para comenzar o
parar el auth-event de la siguiente manera:

    ./agora-admin.py --start id
    ./agora-admin.py --stop id

