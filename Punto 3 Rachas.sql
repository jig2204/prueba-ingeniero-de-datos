/***************TABLAS COMPLEMENTARIAS PARA VALIDACIÓN**********/
--CREATE TABLE TEMPORAL.aux_numeros 
--num INT;/**DESCOMETAR SI SE EJECUTA POR PRIEMRA VEZ*********/
INSERT OVERWRITE temporal.aux_numeros VALUES
(0),(1),(2),(3),(4),(5),(6),(7),(8),(9),
(10),(11),(12),(13),(14),(15),(16),(17),(18),(19),
(20),(21),(22),(23),(24),(25),(26),(27),(28),(29),
(30),(31),(32),(33),(34),(35),(36),(37),(38),(39),
(40),(41),(42),(43),(44),(45),(46),(47),(48),(49),
(50),(51),(52),(53),(54),(55),(56),(57),(58),(59),
(60),(61),(62),(63),(64),(65),(66),(67),(68),(69),
(70),(71),(72),(73),(74),(75),(76),(77),(78),(79),
(80);

WITH
BASE_RACHAS AS(SELECT 
				  identificacion
				 ,corte_mes
				 ,SUM(saldo) AS saldo
			FROM temporal.rachas
			GROUP BY 1, 2
			),
BASE_FECHA AS(
			SELECT 
				  identificacion,
				  MIN(corte_mes) AS fecha_inicio,
				  MAX(CASE
				  		WHEN identificacion = '0TTW5R9RRCJ0A9E5F' THEN '2024-10-10'
				  		WHEN identificacion = '1LFTDYT2H0I9ZGED3S8' THEN '2023-11-11'
				  		WHEN identificacion = '6T645BU8TYM8VGXKO' THEN '2025-01-10'
				  		WHEN identificacion = '869YG73INQB5W1NQT' THEN '2024-12-05'
				  		WHEN identificacion = '1LFTDYT2H0I9ZGED3S8' THEN '2024-01-20'
				  	ELSE corte_mes END 
				  	)AS fecha_fin
			FROM temporal.rachas
			GROUP BY 1
		), 		
BASE_FECHA_2 AS(SELECT identificacion,
				  TO_TIMESTAMP(SUBSTRING(REPLACE(fecha_inicio,'-',''),1,8),'yyyyMMdd')AS fecha_inicio,
				  TO_TIMESTAMP(SUBSTRING(REPLACE(fecha_fin,'-',''),1,8),'yyyyMMdd') AS fecha_fin,
				  int_months_between(TO_TIMESTAMP(SUBSTRING(REPLACE(fecha_fin,'-',''),1,8),'yyyyMMdd'),TO_TIMESTAMP(SUBSTRING(REPLACE(fecha_inicio,'-',''),1,8),'yyyyMMdd')) N 
			 FROM  BASE_FECHA
			 ),
BASE_PRINCIPAL AS (SELECT
				    t.identificacion,
				    from_timestamp(
				        add_months(cast(t.fecha_inicio AS timestamp), n.num),
				        'yyyyMM'
				    ) AS periodo
				FROM BASE_FECHA_2 t
				JOIN temporal.aux_numeros n
				ON n.num <= T.N
				--WHERE t.identificacion = '0TTW5R9RRCJ0A9E5F'/**************quitar filtro */
				ORDER BY t.identificacion, periodo
			  ),
B_GRUPO_SALDO AS(SELECT identificacion
			 	   ,LEFT(REPLACE(corte_mes,"-",""),6) AS fecha_corte
			 	   ,saldo
			 	   /*Clasificar la información por niveles de deuda, así (ver hoja historia):*/
			 	   ,CASE
				  	WHEN saldo > 0 AND saldo < 300000 THEN 'N0'
				  	WHEN saldo >= 300000  AND saldo < 1000000 THEN 'N1'
				  	WHEN saldo >= 1000000 AND saldo < 3000000 THEN 'N2'
				  	WHEN saldo >= 3000000 AND saldo < 5000000 THEN 'N3'
				    ELSE 'N4' END AS clasificacion_saldo
			  FROM  BASE_RACHAS
			  ),
NIVEL_DEUDA AS (
			/*Si un cliente no aparece en un mes específico (después de su primera aparición), se considera que su saldo es N0, excepto si el corte de mes es superior a su fecha de retiro (ver hoja retiros)*/
			SELECT BASE_PRINCIPAL.*,
				  IF(B_GRUPO_SALDO.clasificacion_saldo IS NOT NULL, B_GRUPO_SALDO.clasificacion_saldo,"N0") AS clasificacion_saldo
			FROM BASE_PRINCIPAL
			LEFT JOIN B_GRUPO_SALDO
			ON BASE_PRINCIPAL.identificacion = B_GRUPO_SALDO.identificacion AND CAST(BASE_PRINCIPAL.periodo AS INT) = CAST(B_GRUPO_SALDO.fecha_corte AS INT)
			),
FILTROS AS (SELECT * 
		  FROM  NIVEL_DEUDA
		  WHERE periodo >= '202305' /*Permita realizar todo el ejercicio con base en una fecha específica (fecha_base), es decir, como si estuviera "parado" en una fecha que no necesariamente es el día de hoy.*/
	 		   AND identificacion = '0TTW5R9RRCJ0A9E5F' AND clasificacion_saldo = 'N4' /*Identificar los meses consecutivos (racha) de un cliente dentro de un nivel de saldo.*/
	 	  ORDER BY identificacion, periodo
		),
FILTROS_2  AS( SELECT * 
			FROM(
				SELECT NIVEL_DEUDA.*,
					  row_number() over(partition by  identificacion , clasificacion_saldo order by  periodo asc) as orden 
				FROM NIVEL_DEUDA
				)t
			WHERE orden = 8 /*Seleccionar aquellas rachas que sean mayores o iguales a un número específico n.*/
			),
RACHAS  AS( SELECT T1.identificacion,
			    T1.racha,
			    MAX(t_ra.Periodo) fecha_fin,
			    MAX(t_ra.clasificacion_saldo) nivel_saldo
		  FROM(SELECT identificacion
				    ,MAX(orden) racha
				FROM(
					SELECT NIVEL_DEUDA.*,
						  row_number() over(partition by  identificacion , clasificacion_saldo order by  periodo asc) as orden 
					FROM NIVEL_DEUDA
					)t0
				GROUP BY 1
			  )t1
			LEFT JOIN (SELECT NIVEL_DEUDA.*,
						  row_number() over(partition by  identificacion , clasificacion_saldo order by  periodo asc) as orden 
					 FROM NIVEL_DEUDA
					 )t_ra
			ON t1.identificacion = t_ra.identificacion AND T1.racha = orden
			GROUP BY 1,2
			)
SELECT * 
FROM RACHAS /*El resultado debe presentar para cada cliente:*/
/*Dentro de las subtablas estan la solucion de los puntos, solo hay que nombrarlas para su validacion*/
