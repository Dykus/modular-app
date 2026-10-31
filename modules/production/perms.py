"""Prava modulya "Proizvodstvo" (pokaza zaglushka).

Zdes' pusto, no fayl OBYAZATELEN: yaadro sbiraet prava obxodom vseh moduley,
i esli u module net perms.py - on prosto ne dast nikakix galochek v UI.
Kogda napolnim modul tvoyey Excel-tablicey, prava poyavyatsya syuda,
v tom chisle granularnye na urovne POLYA (kolonki):
    production.edit.field.<imya_kolonki>  - "mozet menyat' tolko etu kolonku"
Eto i est' tot samii sluchai "razreshit' menyat' odnu yacheiku/kolonku".
"""

PERMISSIONS = []
