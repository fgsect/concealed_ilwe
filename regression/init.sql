create table if not exists 
run(
	instance_id integer references instance(rowid),
	method_id integer references method(rowid),
	time float,
	solved integer, -- 1 = solved, 0 = unsolved
	timestamp integer
);

create table if not exists 
instance(
	m integer,
	n integer,
	eta integer,
	tau integer,
	p float,
	seed integer,
	errors integer
);

create table if not exists 
method(
	name string
);

insert into method (name) values ('ILP');
insert into method (name) values ('L1');
insert into method (name) values ('huber');
insert into method (name) values ('cauchy');
insert into method (name) values ('L2');

create view compare as 
select instance.rowid as id,m,n,eta,tau,p,seed, errors,
	printf("%.3f", time_ILP)    as t_ILP,    r1.s as s1, 
	printf("%.3f", time_L1)     as t_L1,     r2.s as s2,
	printf("%.3f", time_huber)  as t_huber,  r3.s as s3,
	printf("%.3f", time_cauchy) as t_cauchy, r4.s as s4,
	printf("%.3f", time_L2)     as t_L2,     r5.s as s5
from instance 
left join (select instance_id,time as time_ILP,    solved as s from run where method_id = 1) r1 on instance.rowid = r1.instance_id 
left join (select instance_id,time as time_L1,     solved as s from run where method_id = 2) r2 on instance.rowid = r2.instance_id
left join (select instance_id,time as time_huber,  solved as s from run where method_id = 3) r3 on instance.rowid = r3.instance_id
left join (select instance_id,time as time_cauchy, solved as s from run where method_id = 4) r4 on instance.rowid = r4.instance_id
left join (select instance_id,time as time_L2,     solved as s from run where method_id = 5) r5 on instance.rowid = r5.instance_id;

create view success_count as 
select n,m,p,sum(s1) ILP, sum(s2) L1,sum(s3) huber,sum(s4) cauchy,sum(s5) L2 from compare group by n,m,p order by p,m;

create view success_chance as
select r1.m as m, r1.errors as errors, success, total, printf("%.3f", 1.0*success/total) as chance from (select errors,m, count(*) success from compare where errors < 100 and s2 = 1 group by errors,m) as r1, (select errors,m, count(*) total from compare where errors < 100 group by errors,m) as r2 where r1.errors = r2.errors and r1.m = r2.m order by m, errors;
-- .mode csv
-- .output success_chance.csv
-- select * from success_chance;
