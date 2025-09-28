resource "aws_route53_record" "api" {
  zone_id = "Z02680423BHWEVRU2JZDQ"
  name    = "kh.asses2.cab432.com"
  type    = "CNAME"
  ttl     = "300"
  records = ["ec2-13-239-136-127.ap-southeast-2.compute.amazonaws.com"]
}

output "domain_name" {
  value = aws_route53_record.api.fqdn
}